"""
Кешування каталогу (Redis).

Щоб не видаляти кожен ключ окремо, використовую "версію каталогу":
всі ключі кешу містять номер версії, і коли щось змінюється в адмінці -
сигнал просто збільшує версію. Старі ключі більше ніхто не читає,
а Redis сам їх видалить по TIMEOUT.
"""
from django.core.cache import cache
from django.db.models import Count, F, Q
from django.http import Http404

from .models import Category, Product

VERSION_KEY = 'catalog:version'
TIMEOUT = 60 * 15  # 15 хвилин


def get_version():
    version = cache.get(VERSION_KEY)
    if version is None:
        version = 1
        cache.set(VERSION_KEY, version, None)  # None = зберігати назавжди
    return version


def invalidate_catalog():
    """Викликається з сигналів, коли змінилась гра / категорія / новина."""
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        # ключа ще не було
        cache.set(VERSION_KEY, 2, None)


def _key(name):
    return f'catalog:v{get_version()}:{name}'


def get_categories():
    """Категорії + кількість активних ігор у кожній."""
    key = _key('categories')
    data = cache.get(key)
    if data is None:
        data = list(Category.objects.annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        ))
        cache.set(key, data, TIMEOUT)
    return data


def get_home_data():
    """Всі блоки сторінки Цікавинки одним шматком."""
    from news.models import News  # імпорт тут, щоб не було циклічного імпорту

    key = _key('home')
    data = cache.get(key)
    if data is None:
        products = Product.objects.filter(is_active=True).select_related('category')
        featured = list(products.filter(is_featured=True)[:6]) or list(products[:6])
        data = {
            'featured': featured,
            'discounts': list(products.filter(discount_price__isnull=False, discount_price__lt=F('price'))[:5]),
            'free_games': list(products.filter(price=0)[:5]),
            'new_releases': list(products.exclude(release_date=None).order_by('-release_date')[:5]),
            'latest_news': list(News.objects.filter(is_published=True).select_related('product')[:3]),
        }
        cache.set(key, data, TIMEOUT)
    return data


def get_product(slug):
    """Гра для сторінки деталей (разом з категорією і скріншотами)."""
    key = _key(f'product:{slug}')
    product = cache.get(key)
    if product is None:
        product = (
            Product.objects.select_related('category')
            .prefetch_related('images')
            .filter(slug=slug, is_active=True)
            .first()
        )
        if product is None:
            raise Http404('Гру не знайдено')
        cache.set(key, product, TIMEOUT)
    return product
