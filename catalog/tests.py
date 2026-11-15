import json
import os
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO, StringIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from PIL import Image

from .management.commands.fetch_covers import pick_best_match
from .models import Category, Product

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'catalog-tests'}}


def make_product(title, slug, price='10.00', **kwargs):
    return Product.objects.create(title=title, slug=slug, price=Decimal(price), **kwargs)


class ProductModelTests(TestCase):
    def test_discount(self):
        p = make_product('Гра', 'gra', price='20.00', discount_price=Decimal('15.00'))
        self.assertTrue(p.has_discount())
        self.assertEqual(p.final_price(), Decimal('15.00'))
        self.assertEqual(p.discount_percent(), 25)

    def test_discount_bigger_than_price_is_ignored(self):
        p = make_product('Гра', 'gra', price='10.00', discount_price=Decimal('12.00'))
        self.assertFalse(p.has_discount())
        self.assertEqual(p.final_price(), Decimal('10.00'))
        self.assertEqual(p.discount_percent(), 0)

    def test_free(self):
        self.assertTrue(make_product('Free', 'free', price='0').is_free())

    def test_absolute_url(self):
        p = make_product('Гра', 'my-game')
        self.assertEqual(p.get_absolute_url(), '/game/my-game/')


class CatalogViewTests(TestCase):
    def setUp(self):
        self.action = Category.objects.create(name='Екшн', slug='action')
        self.rpg = Category.objects.create(name='RPG', slug='rpg')
        self.cheap = make_product('Cheap Shooter', 'cheap', price='5.00', category=self.action, developer='Indie Team')
        self.expensive = make_product('Big RPG', 'big-rpg', price='60.00', category=self.rpg)
        self.hidden = make_product('Hidden Game', 'hidden', is_active=False)

    def test_home_page(self):
        response = self.client.get(reverse('catalog:home'))
        self.assertEqual(response.status_code, 200)

    def test_list_shows_only_active(self):
        response = self.client.get(reverse('catalog:product_list'))
        self.assertContains(response, 'Cheap Shooter')
        self.assertNotContains(response, 'Hidden Game')

    def test_search_by_developer(self):
        # пошук через Q шукає не тільки в назві
        response = self.client.get(reverse('catalog:product_list'), {'q': 'indie'})
        self.assertContains(response, 'Cheap Shooter')
        self.assertNotContains(response, 'Big RPG')

    def test_filter_by_category(self):
        response = self.client.get(reverse('catalog:product_list'), {'category': 'rpg'})
        self.assertEqual(list(response.context['products']), [self.expensive])

    def test_unknown_category_404(self):
        response = self.client.get(reverse('catalog:product_list'), {'category': 'nope'})
        self.assertEqual(response.status_code, 404)

    def test_filter_by_max_price(self):
        response = self.client.get(reverse('catalog:product_list'), {'max_price': '10'})
        self.assertEqual(list(response.context['products']), [self.cheap])

    def test_sort_by_price(self):
        response = self.client.get(reverse('catalog:product_list'), {'sort': 'price_desc'})
        self.assertEqual(list(response.context['products']), [self.expensive, self.cheap])

    def count_queries(self, url):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx.captured_queries)

    def test_list_has_no_n_plus_1(self):
        # перевірка на N+1: кількість запитів не росте разом з кількістю ігор
        url = reverse('catalog:product_list')
        before = self.count_queries(url)
        for i in range(10):
            make_product(f'Extra {i}', f'extra-{i}', category=self.action)
        self.assertEqual(self.count_queries(url), before)

    def test_detail_page_and_recently_viewed(self):
        response = self.client.get(self.cheap.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['recently_viewed'], [self.cheap.id])

    def test_inactive_detail_404(self):
        response = self.client.get(self.hidden.get_absolute_url())
        self.assertEqual(response.status_code, 404)


@override_settings(CACHES=LOCMEM_CACHE)
class CatalogCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_cache_is_cleared_when_product_changes(self):
        product = make_product('Old Title', 'game', is_featured=True)
        self.assertContains(self.client.get(reverse('catalog:home')), 'Old Title')

        # сигнал post_save має скинути кеш, і на сторінці одразу нова назва
        product.title = 'New Title'
        product.save()
        response = self.client.get(reverse('catalog:home'))
        self.assertContains(response, 'New Title')
        self.assertNotContains(response, 'Old Title')

    def test_banner_has_cover_fallback(self):
        make_product('Game', 'game', is_featured=True, banner='banners/game.jpg', cover='covers/game.jpg')
        response = self.client.get(reverse('catalog:home'))
        self.assertContains(response, 'src="/media/banners/game.jpg"')
        self.assertContains(response, 'data-fallback="/media/covers/game.jpg"')

    def test_fetch_covers_clears_home_cache(self):
        from .cache import get_version
        product = make_product('Hades', 'hades', is_featured=True)
        self.client.get(reverse('catalog:home'))  # головна тепер у кеші
        version = get_version()

        search = {'results': [{'id': 1, 'name': 'Hades', 'added': 1, 'background_image': 'https://m.test/a.jpg'}]}

        def fake_urlopen(request, timeout):
            if '/screenshots' in request.full_url:
                return BytesIO(b'{"results": []}')
            if request.full_url.startswith('https://api.rawg.io/'):
                return BytesIO(json.dumps(search).encode())
            return BytesIO(fake_jpeg())

        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with self.settings(MEDIA_ROOT=media),                 patch.dict(os.environ, {'RAWG_API_KEY': 'k'}),                 patch('catalog.management.commands.fetch_covers.urlopen', side_effect=fake_urlopen),                 patch('catalog.management.commands.fetch_covers.time.sleep'):
            call_command('fetch_covers', stdout=StringIO())

        # сигнал post_save скинув кеш - головна покаже новий банер
        self.assertGreater(get_version(), version)
        response = self.client.get(reverse('catalog:home'))
        self.assertContains(response, 'src="/media/banners/hades.jpg"')
        product.refresh_from_db()
        self.assertEqual(product.banner.name, 'banners/hades.jpg')

    def test_home_is_cached(self):
        make_product('Game', 'game')
        self.client.get(reverse('catalog:home'))
        # другий раз ігри беруться з кешу - запитів до таблиці ігор нема
        with self.assertNumQueries(0):
            self.client.get(reverse('catalog:home'))


class HomeGenresTests(TestCase):
    def test_genre_block_on_home(self):
        action = Category.objects.create(name='Екшн', slug='action', image='categories/action.jpg')
        Category.objects.create(name='Порожня', slug='empty')  # без ігор - не показуємо
        make_product('Game', 'game', category=action)
        response = self.client.get(reverse('catalog:home'))
        self.assertContains(response, 'Обрати за жанром')
        self.assertContains(response, '/browse/?category=action')
        self.assertContains(response, 'categories/action.jpg')
        self.assertNotContains(response, 'category=empty')


def fake_jpeg(size=(800, 450)):
    buf = BytesIO()
    Image.new('RGB', size, (200, 30, 30)).save(buf, format='JPEG')
    return buf.getvalue()


class FetchCoversTests(TestCase):
    """Без справжніх запитів в інтернет: urlopen підмінений."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_without_key_gives_clear_error(self):
        with patch.dict(os.environ):
            os.environ.pop('RAWG_API_KEY', None)
            with self.assertRaisesMessage(CommandError, 'RAWG_API_KEY'):
                call_command('fetch_covers', stdout=StringIO())

    def test_pick_best_match(self):
        results = [
            {'id': 1, 'name': 'God of War I', 'added': 2000, 'background_image': 'https://x/1.jpg'},
            {'id': 2, 'name': 'Hades', 'added': 3, 'background_image': 'https://x/2.jpg'},  # дублікат
            {'id': 3, 'name': 'HADES', 'added': 9000, 'background_image': 'https://x/3.jpg'},
            {'id': 4, 'name': 'Hades', 'added': 99999, 'background_image': None},  # без картинки
        ]
        self.assertEqual(pick_best_match('Hades', results)['id'], 3)
        self.assertIsNone(pick_best_match('Cyberpunk 2077', results))

    def test_command_parses_rawg_response(self):
        game = make_product('Hades', 'hades')
        # обкладинка, завантажена вручну через адмінку - її не можна чіпати
        own = make_product('Celeste', 'celeste', cover='covers/my_upload.png')

        search = {'results': [
            {'id': 10, 'name': 'Hades II', 'added': 500, 'background_image': 'https://media.test/h2.jpg'},
            {'id': 11, 'name': 'Hades', 'added': 9000, 'background_image': 'https://media.test/hades.jpg'},
        ]}
        shots = {'results': [{'image': f'https://media.test/s{i}.jpg'} for i in range(6)]}
        requested = []

        def fake_urlopen(request, timeout):
            url = request.full_url
            requested.append(url)
            self.assertEqual(timeout, 15)
            if url.startswith('https://api.rawg.io/api/games?'):
                return BytesIO(json.dumps(search).encode())
            if url.startswith('https://api.rawg.io/api/games/11/screenshots?'):
                return BytesIO(json.dumps(shots).encode())
            self.assertNotIn('secret-key', url)  # ключ не йде на сервер картинок
            return BytesIO(fake_jpeg())

        out = StringIO()
        with self.settings(MEDIA_ROOT=self.media),                 patch.dict(os.environ, {'RAWG_API_KEY': 'secret-key'}),                 patch('catalog.management.commands.fetch_covers.urlopen', side_effect=fake_urlopen),                 patch('catalog.management.commands.fetch_covers.time.sleep'):
            call_command('fetch_covers', 'hades', 'celeste', stdout=out)

            game.refresh_from_db()
            self.assertEqual(game.cover.name, 'covers/hades.jpg')
            self.assertEqual(Image.open(game.cover.path).size, (600, 800))
            self.assertEqual(game.banner.name, 'banners/hades.jpg')
            self.assertEqual(Image.open(game.banner.path).size, (1600, 900))
            self.assertEqual(game.images.count(), 4)  # максимум 4 скріншоти

        own.refresh_from_db()
        self.assertEqual(own.cover.name, 'covers/my_upload.png')
        self.assertIn('https://media.test/hades.jpg', requested)
        self.assertNotIn('secret-key', out.getvalue())
