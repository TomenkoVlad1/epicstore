"""
Заповнює базу категоріями, іграми, новинами та генерує картинки.

    python manage.py seed_games              - додати все (дублікатів не буде)
    python manage.py seed_games --no-images  - без картинок (швидше)
    python manage.py seed_games --redraw     - перемалювати картинки, навіть якщо вони вже є

--redraw перемальовує тільки згенеровані файли (<папка>/<slug>.jpg).
Картинки, завантажені вручну через адмінку, не чіпаються ніколи.
Увага: обкладинки з RAWG (fetch_covers) теж мають ім'я <slug>.jpg, тож після
--redraw їх треба завантажити знову: python manage.py fetch_covers
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Category, Product, ProductImage
from news.models import News

from ._images import (
    is_generated, make_banner, make_category_image, make_cover, make_news_image, make_screenshot,
    save_generated,
)
from ._seed_data import CATEGORIES, GAMES, NEWS


class Command(BaseCommand):
    help = 'Додає категорії, ігри, новини і генерує для них картинки'

    def add_arguments(self, parser):
        parser.add_argument('--no-images', action='store_true', help='Не генерувати картинки')
        parser.add_argument('--redraw', action='store_true', help='Перемалювати всі картинки')

    @transaction.atomic
    def handle(self, *args, **options):
        with_images = not options['no_images']
        redraw = options['redraw']

        categories = {}
        for name, slug in CATEGORIES:
            categories[slug], _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})

        # картинки для всіх категорій, включно з доданими через адмінку
        # (для невідомого жанру draw_emblem малює ромб)
        if with_images:
            for category in Category.objects.all():
                name = f'{category.slug}.jpg'
                if is_generated(category.image, name) and (redraw or not category.image):
                    save_generated(category.image, name, make_category_image(category.slug))
                    category.save(update_fields=['image'])

        new_games = 0
        for (title, slug, cat, price, discount, dev, pub, release, featured, description) in GAMES:
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'category': categories[cat],
                    'price': Decimal(price),
                    'discount_price': Decimal(discount) if discount else None,
                    'developer': dev,
                    'publisher': pub,
                    'release_date': release,
                    'is_featured': featured,
                    'description': description,
                },
            )
            new_games += created

            if with_images:
                self.draw_game_images(product, categories[cat].name, description, redraw)
            self.stdout.write(f'  {"+" if created else "·"} {title}')

        new_news = 0
        now = timezone.now()
        for i, (title, slug, game_slug, short, text) in enumerate(NEWS):
            item, created = News.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'short_text': short,
                    'text': text,
                    'product': Product.objects.filter(slug=game_slug).first() if game_slug else None,
                },
            )
            if created:
                # різні дати, щоб новини йшли по порядку, а не з однаковим часом
                News.objects.filter(pk=item.pk).update(created_at=now - timedelta(days=i * 2))
                new_news += 1
            if with_images and is_generated(item.image, f'{slug}.jpg') and (redraw or not item.image):
                save_generated(item.image, f'{slug}.jpg', make_news_image(title))
                item.save(update_fields=['image'])

        self.stdout.write(self.style.SUCCESS(
            f'Готово! Категорій: {len(categories)}, ігор: {len(GAMES)} (нових {new_games}), '
            f'новин: {len(NEWS)} (нових {new_news})'
        ))

    def draw_game_images(self, product, category_name, description, redraw):
        name = f'{product.slug}.jpg'
        changed = False
        # перемальовуємо тільки свої файли, а якщо картинки ще нема - малюємо
        if is_generated(product.cover, name) and (redraw or not product.cover):
            save_generated(product.cover, name, make_cover(product.title, category_name))
            changed = True
        if is_generated(product.banner, name) and (redraw or not product.banner):
            subtitle = description.split('.')[0][:60]
            save_generated(product.banner, name, make_banner(product.title, subtitle))
            changed = True
        if changed:
            product.save()

        shots = list(product.images.all())
        all_generated = all(is_generated(shot.image, f'{product.slug}-{shot.order}.jpg') for shot in shots)
        if shots and not (redraw and all_generated):
            return
        product.images.all().delete()  # видаляє тільки записи в базі, файли перезапишуться нижче
        for n in range(1, 4):
            shot = ProductImage(product=product, order=n)
            save_generated(shot.image, f'{product.slug}-{n}.jpg', make_screenshot(product.title, n))
            shot.save()
