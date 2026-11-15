from decimal import Decimal

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

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

    def test_home_is_cached(self):
        make_product('Game', 'game')
        self.client.get(reverse('catalog:home'))
        # другий раз ігри беруться з кешу - запитів до таблиці ігор нема
        with self.assertNumQueries(0):
            self.client.get(reverse('catalog:home'))
