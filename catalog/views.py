from decimal import Decimal, InvalidOperation

from django.db.models import Q, F
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import render

from cart.cart import Cart
from library.models import LibraryItem
from .cache import get_categories, get_home_data, get_product
from .context_processors import add_to_recently_viewed
from .models import Product

# варіанти сортування: що в url -> (назва для юзера, поле для order_by)
SORT_OPTIONS = {
    'new': ('Нещодавно додані', '-created_at'),
    'release': ('Дата виходу', '-release_date'),
    'title': ('За алфавітом', 'title'),
    'price_asc': ('Ціна: за зростанням', 'real_price'),
    'price_desc': ('Ціна: за спаданням', '-real_price'),
}


def to_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


def home(request):
    """Цікавинки - головна сторінка крамниці. Всі блоки беруться з кешу."""
    return render(request, 'catalog/home.html', get_home_data())


def product_list(request):
    # select_related - категорія підтягується одним запитом з JOIN, а не окремо для кожної гри
    # real_price - ціна з урахуванням знижки, щоб по ній можна було сортувати і фільтрувати
    products = (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .annotate(real_price=Coalesce('discount_price', 'price'))
    )

    # категорії з кількістю ігор - з кешу
    categories = get_categories()

    # --- пошук ---
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(developer__icontains=query)
            | Q(publisher__icontains=query)
            | Q(category__name__icontains=query)
        )

    # --- фільтри ---
    current_category = None
    category_slug = request.GET.get('category')
    if category_slug:
        current_category = next((c for c in categories if c.slug == category_slug), None)
        if current_category is None:
            raise Http404('Категорію не знайдено')
        products = products.filter(category_id=current_category.id)

    min_price = to_decimal(request.GET.get('min_price'))
    max_price = to_decimal(request.GET.get('max_price'))
    if min_price is not None:
        products = products.filter(real_price__gte=min_price)
    if max_price is not None:
        products = products.filter(real_price__lte=max_price)

    if request.GET.get('free'):
        products = products.filter(price=0)

    if request.GET.get('discount'):
        products = products.filter(discount_price__isnull=False, discount_price__lt=F('price'))

    # --- сортування ---
    sort = request.GET.get('sort', 'new')
    if sort not in SORT_OPTIONS:
        sort = 'new'
    products = products.order_by(SORT_OPTIONS[sort][1])

    context = {
        'products': products,
        'categories': categories,
        'current_category': current_category,
        'query': query,
        'sort': sort,
        'sort_options': SORT_OPTIONS,
        'min_price': request.GET.get('min_price', ''),
        'max_price': request.GET.get('max_price', ''),
        'free': request.GET.get('free'),
        'discount': request.GET.get('discount'),
    }
    return render(request, 'catalog/product_list.html', context)


def product_detail(request, slug):
    product = get_product(slug)  # з кешу, разом з категорією і скріншотами
    add_to_recently_viewed(request, product)

    owned = (
        request.user.is_authenticated
        and LibraryItem.objects.filter(user=request.user, product=product).exists()
    )

    context = {
        'product': product,
        'images': product.images.all(),  # вже підвантажені через prefetch_related
        'in_cart': product in Cart(request),
        'owned': owned,
    }
    return render(request, 'catalog/product_detail.html', context)
