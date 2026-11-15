from .models import Product

RECENTLY_VIEWED_KEY = 'recently_viewed'
RECENTLY_VIEWED_LIMIT = 10


def add_to_recently_viewed(request, product):
    """Викликаю в product_detail - кладе id гри на початок списку в сесії."""
    ids = request.session.get(RECENTLY_VIEWED_KEY, [])
    if product.id in ids:
        ids.remove(product.id)
    ids.insert(0, product.id)
    request.session[RECENTLY_VIEWED_KEY] = ids[:RECENTLY_VIEWED_LIMIT]


def recently_viewed(request):
    ids = request.session.get(RECENTLY_VIEWED_KEY, [])
    if not ids:
        return {'recently_viewed': []}

    # in_bulk повертає словник {id: product}, одним запитом
    products = Product.objects.filter(is_active=True).in_bulk(ids)
    # зберігаємо порядок як в сесії (останній переглянутий - перший)
    result = [products[i] for i in ids if i in products]
    return {'recently_viewed': result}
