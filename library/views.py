from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog.models import Category
from .models import LibraryItem, Collection

SORT_OPTIONS = {
    'recent': ('Нещодавні придбання', '-purchased_at'),
    'az': ('За алфавітом: А-Я', 'product__title'),
    'za': ('За алфавітом: Я-А', '-product__title'),
}


@login_required
def library(request):
    items = (
        LibraryItem.objects.filter(user=request.user)
        .select_related('product', 'product__category')
        .prefetch_related('collections')
    )
    collections = request.user.collections.all()

    # вкладки: all / fav / id колекції
    tab = request.GET.get('tab', 'all')
    current_collection = None
    if tab == 'fav':
        items = items.filter(is_favorite=True)
    elif tab.isdigit():
        current_collection = get_object_or_404(Collection, id=tab, user=request.user)
        items = items.filter(collections=current_collection)
    else:
        tab = 'all'

    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(product__title__icontains=q)

    category = request.GET.get('category', '')
    if category:
        items = items.filter(product__category__slug=category)

    sort = request.GET.get('sort', 'recent')
    if sort not in SORT_OPTIONS:
        sort = 'recent'
    items = items.order_by(SORT_OPTIONS[sort][1])

    context = {
        'items': items,
        'collections': collections,
        'tab': tab,
        'current_collection': current_collection,
        'q': q,
        'category': category,
        # тільки ті жанри, які є в бібліотеці
        'categories': Category.objects.filter(products__owners__user=request.user).distinct(),
        'sort': sort,
        'sort_options': SORT_OPTIONS,
    }
    return render(request, 'library/library.html', context)


def back_to_library(request):
    # повертаємось на ту ж вкладку, де були (і перевіряємо що посилання з нашого сайту)
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('library:library')


@login_required
@require_POST
def toggle_favorite(request, pk):
    item = get_object_or_404(LibraryItem.objects.select_related('product'), pk=pk, user=request.user)
    item.is_favorite = not item.is_favorite
    item.save()
    if item.is_favorite:
        messages.success(request, f'«{item.product.title}» додано в улюблені')
    else:
        messages.info(request, f'«{item.product.title}» прибрано з улюблених')
    return back_to_library(request)


@login_required
@require_POST
def collection_create(request):
    name = request.POST.get('name', '').strip()
    if name:
        collection = Collection.objects.create(user=request.user, name=name[:50])
        messages.success(request, f'Колекцію «{collection.name}» створено')
        return redirect(reverse('library:library') + f'?tab={collection.id}')
    messages.error(request, 'Введіть назву колекції')
    return redirect('library:library')


@login_required
@require_POST
def collection_delete(request, pk):
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    collection.delete()  # ігри залишаються в бібліотеці, видаляється тільки колекція
    messages.info(request, f'Колекцію «{collection.name}» видалено')
    return redirect('library:library')


@login_required
@require_POST
def collection_toggle(request, pk, item_id):
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    item = get_object_or_404(LibraryItem.objects.select_related('product'), pk=item_id, user=request.user)
    if collection.items.filter(pk=item.pk).exists():
        collection.items.remove(item)
        messages.info(request, f'«{item.product.title}» прибрано з «{collection.name}»')
    else:
        collection.items.add(item)
        messages.success(request, f'«{item.product.title}» додано в «{collection.name}»')
    return back_to_library(request)
