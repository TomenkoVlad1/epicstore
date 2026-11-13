from django.shortcuts import render, get_object_or_404
from .models import Category, Product


def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()

    # фільтр по категорії ?category=slug
    current_category = None
    category_slug = request.GET.get('category')
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=current_category)

    # пошук ?q=...
    query = request.GET.get('q', '')
    if query:
        products = products.filter(title__icontains=query)

    context = {
        'products': products,
        'categories': categories,
        'current_category': current_category,
        'query': query,
    }
    return render(request, 'catalog/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    context = {
        'product': product,
        'images': product.images.all(),
    }
    return render(request, 'catalog/product_detail.html', context)
