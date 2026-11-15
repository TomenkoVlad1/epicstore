"""
Завантажує справжні обкладинки, банери і скріншоти ігор з RAWG (https://rawg.io).

    python manage.py fetch_covers                  - для всіх ігор
    python manage.py fetch_covers gta-5 hades      - тільки для цих slug-ів
    python manage.py fetch_covers --force          - перезаписати і картинки, завантажені вручну
    python manage.py fetch_covers --dry-run        - тільки пошук, без завантаження картинок

Ключ береться зі змінної середовища RAWG_API_KEY (settings читає її з .env).
Без --force перезаписуються тільки згенеровані картинки: covers/<slug>.jpg,
banners/<slug>.jpg і screenshots/<slug>-<n>.jpg. Все, що завантажено через адмінку, не чіпаємо.
"""
import difflib
import json
import os
import re
import time
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageOps, UnidentifiedImageError

from catalog.models import Product, ProductImage

from ._images import is_generated, save_generated

API_URL = 'https://api.rawg.io/api'
TIMEOUT = 15             # секунд на один запит
PAUSE = 0.3              # пауза між запитами, щоб не навантажувати RAWG
MAX_SCREENSHOTS = 4
MAX_DOWNLOAD = 25 * 1024 * 1024  # більші файли не качаємо
USER_AGENT = 'epicstore-study-project/1.0'

COVER_SIZE = (600, 800)       # 3:4
BANNER_SIZE = (1600, 900)     # 16:9
SCREENSHOT_SIZE = (1280, 720)

# Наша назва -> як гра називається в RAWG. Потрібно, коли пошук за нашою назвою
# знаходить не ту гру (стару частину або порожню сторінку-дублікат від користувача).
TITLE_HINTS = {
    'PUBG: Battlegrounds': "PlayerUnknown's Battlegrounds",
    'God of War': 'God of War (2018)',
    'Fall Guys': 'Fall Guys: Ultimate Knockout',
    'Fortnite': 'Fortnite Battle Royale',
    'Trackmania': 'TrackMania (2020)',
}

# Мінімальна схожість назв (0..1), щоб вважати результат тією самою грою
MIN_SIMILARITY = 0.75


class RawgError(Exception):
    pass


def normalize(title):
    """'The Witcher 3: Wild Hunt™' -> 'the witcher 3 wild hunt'"""
    title = title.lower().replace('&', ' and ')
    title = re.sub(r'[^\w\s]', ' ', title)
    return ' '.join(title.split())


def pick_best_match(title, results):
    """
    Вибирає з результатів пошуку RAWG гру з найближчою назвою.
    Якщо однакових назв кілька (в RAWG бувають дублікати), бере найпопулярнішу
    (поле added - скільки людей додали гру собі). Ігри без картинки пропускаються.
    Повертає dict гри або None, якщо нічого достатньо схожого.
    """
    target = normalize(title)
    best, best_key = None, None
    for game in results:
        if not game.get('background_image'):
            continue
        score = difflib.SequenceMatcher(None, target, normalize(game.get('name', ''))).ratio()
        if score < MIN_SIMILARITY:
            continue
        key = (score, game.get('added') or 0)
        if best_key is None or key > best_key:
            best, best_key = game, key
    return best


def load_image(data):
    """Перевіряє, що байти - справжня картинка, і повертає її в RGB."""
    try:
        Image.open(BytesIO(data)).verify()  # verify() ловить биті файли
        img = Image.open(BytesIO(data))      # після verify() картинку треба відкрити заново
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as e:
        raise RawgError(f'не картинка або пошкоджений файл ({e.__class__.__name__})')
    if img.width < 200 or img.height < 200:
        raise RawgError(f'занадто маленька картинка {img.width}x{img.height}')
    return img.convert('RGB')


def to_jpeg(img, size, quality=88):
    """Обрізає по центру до потрібних пропорцій і зменшує до size."""
    fitted = ImageOps.fit(img, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    buf = BytesIO()
    fitted.save(buf, format='JPEG', quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


class RawgClient:
    def __init__(self, api_key, pause=PAUSE):
        self.api_key = api_key
        self.pause = pause

    def _hide_key(self, text):
        return str(text).replace(self.api_key, '***')

    def _download(self, url):
        time.sleep(self.pause)
        request = Request(url, headers={'User-Agent': USER_AGENT})
        try:
            with urlopen(request, timeout=TIMEOUT) as response:
                data = response.read(MAX_DOWNLOAD + 1)
        except HTTPError as e:
            if e.code in (401, 403) and url.startswith(API_URL):
                raise CommandError('RAWG відхилив ключ (HTTP %s). Перевір RAWG_API_KEY у .env' % e.code)
            raise RawgError(f'HTTP {e.code}')
        except (URLError, TimeoutError, OSError) as e:
            # у тексті помилки може опинитись url з ключем - ховаємо
            raise RawgError(self._hide_key(getattr(e, 'reason', e)))
        if len(data) > MAX_DOWNLOAD:
            raise RawgError('файл завеликий')
        return data

    def api(self, path, **params):
        params['key'] = self.api_key
        data = self._download(f'{API_URL}{path}?{urlencode(params)}')
        try:
            return json.loads(data)
        except ValueError:
            raise RawgError('RAWG повернув не JSON')

    def search(self, title):
        data = self.api('/games', search=title, search_precise='true', page_size=5)
        return data.get('results') or []

    def screenshots(self, game_id):
        data = self.api(f'/games/{game_id}/screenshots', page_size=MAX_SCREENSHOTS + 2)
        return [s['image'] for s in data.get('results') or [] if s.get('image')]

    def image(self, url):
        # картинки качаємо тільки по https і без ключа в адресі
        if urlparse(url).scheme != 'https':
            raise RawgError('посилання на картинку не https')
        return load_image(self._download(url))


class Command(BaseCommand):
    help = 'Завантажує обкладинки, банери і скріншоти ігор з RAWG API'

    def add_arguments(self, parser):
        parser.add_argument('slugs', nargs='*', help='slug-и ігор (за замовчуванням - всі)')
        parser.add_argument('--force', action='store_true',
                            help='Перезаписати і картинки, завантажені вручну через адмінку')
        parser.add_argument('--dry-run', action='store_true', help='Тільки знайти ігри, нічого не зберігати')

    def handle(self, *args, **options):
        api_key = os.environ.get('RAWG_API_KEY', '').strip()
        if not api_key:
            raise CommandError(
                'Не задано RAWG_API_KEY. Отримай безкоштовний ключ на https://rawg.io/apidocs '
                'і додай у файл .env рядок RAWG_API_KEY=<твій ключ>'
            )
        client = RawgClient(api_key)
        self.force = options['force']
        self.dry_run = options['dry_run']

        products = Product.objects.order_by('title').prefetch_related('images')
        if options['slugs']:
            products = products.filter(slug__in=options['slugs'])

        found, not_found, skipped, errors = [], [], [], []
        for product in products:
            try:
                result = self.process(client, product)
            except RawgError as e:
                errors.append(f'{product.title}: {e}')
                self.stdout.write(self.style.ERROR(f'  ! {product.title}: {e}'))
                continue
            if result is None:
                skipped.append(product.title)
                self.stdout.write(f'  · {product.title}: пропущено (картинки завантажені вручну)')
            elif result is False:
                not_found.append(product.title)
                self.stdout.write(self.style.WARNING(f'  ? {product.title}: не знайдено'))
            else:
                found.append(f'{product.title} -> {result}')
                self.stdout.write(self.style.SUCCESS(f'  + {product.title} -> {result}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Знайдено: {len(found)}'))
        for line in found:
            self.stdout.write(f'    {line}')
        if not_found:
            self.stdout.write(self.style.WARNING(f'Не знайдено: {len(not_found)}'))
            for title in not_found:
                self.stdout.write(f'    {title}')
        if skipped:
            self.stdout.write(f'Пропущено (свої картинки, див. --force): {len(skipped)}')
            for title in skipped:
                self.stdout.write(f'    {title}')
        if errors:
            self.stdout.write(self.style.ERROR(f'Помилки: {len(errors)}'))
            for line in errors:
                self.stdout.write(f'    {line}')

    def process(self, client, product):
        """None - пропущено, False - не знайдено, інакше рядок з описом що оновлено."""
        name = f'{product.slug}.jpg'
        shots = list(product.images.all())
        can_cover = self.force or is_generated(product.cover, name)
        can_banner = self.force or is_generated(product.banner, name)
        can_shots = self.force or all(
            is_generated(shot.image, f'{product.slug}-{shot.order}.jpg') for shot in shots
        )
        if not (can_cover or can_banner or can_shots):
            return None

        query = TITLE_HINTS.get(product.title, product.title)
        game = pick_best_match(query, client.search(query))
        if game is None:
            return False
        if self.dry_run:
            return f'{game["name"]} (id {game["id"]})'

        updated = []
        if can_cover or can_banner:
            art = client.image(game['background_image'])
            if can_cover:
                save_generated(product.cover, name, to_jpeg(art, COVER_SIZE))
                updated.append('обкладинка')
            if can_banner:
                save_generated(product.banner, name, to_jpeg(art, BANNER_SIZE))
                updated.append('банер')
            product.save(update_fields=['cover', 'banner'])

        if can_shots:
            new_shots = []
            for url in client.screenshots(game['id']):
                if len(new_shots) == MAX_SCREENSHOTS:
                    break
                try:
                    new_shots.append(to_jpeg(client.image(url), SCREENSHOT_SIZE, quality=82))
                except RawgError:
                    continue  # одна бита картинка - не причина пропускати всю гру
            if new_shots:
                product.images.all().delete()  # тільки записи в базі, файли перезапишуться
                for n, data in enumerate(new_shots, start=1):
                    shot = ProductImage(product=product, order=n)
                    save_generated(shot.image, f'{product.slug}-{n}.jpg', data)
                    shot.save()
                updated.append(f'скріншоти: {len(new_shots)}')

        return f'{game["name"]} ({", ".join(updated) or "нічого не змінено"})'
