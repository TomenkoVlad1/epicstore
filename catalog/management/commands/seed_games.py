"""
Заповнює базу категоріями, іграми, новинами та генерує картинки.

    python manage.py seed_games              - додати все (дублікатів не буде)
    python manage.py seed_games --no-images  - без картинок (швидше)
    python manage.py seed_games --redraw     - перемалювати картинки, навіть якщо вони вже є
"""
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Category, Product, ProductImage
from news.models import News

from ._images import make_banner, make_cover, make_news_image, make_screenshot
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
            if with_images and (redraw or not item.image):
                item.image.save(f'{slug}.jpg', ContentFile(make_news_image(title)), save=True)

        self.stdout.write(self.style.SUCCESS(
            f'Готово! Категорій: {len(categories)}, ігор: {len(GAMES)} (нових {new_games}), '
            f'новин: {len(NEWS)} (нових {new_news})'
        ))

    def draw_game_images(self, product, category_name, description, redraw):
        changed = False
        if redraw or not product.cover:
            product.cover.save(f'{product.slug}.jpg', ContentFile(make_cover(product.title, category_name)), save=False)
            changed = True
        if redraw or not product.banner:
            subtitle = description.split('.')[0][:60]
            product.banner.save(f'{product.slug}.jpg', ContentFile(make_banner(product.title, subtitle)), save=False)
            changed = True
        if changed:
            product.save()

        if redraw:
            product.images.all().delete()
        if not product.images.exists():
            for n in range(1, 4):
                shot = ProductImage(product=product, order=n)
                shot.image.save(f'{product.slug}-{n}.jpg', ContentFile(make_screenshot(product.title, n)), save=False)
                shot.save()
