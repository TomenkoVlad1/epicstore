from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from catalog.models import Product
from core.ratelimit import ratelimit
from library.models import LibraryItem
from users.models import UserProfile
from .cart import Cart


def cart_detail(request):
    cart = Cart(request)
    context = {
        'products': cart.get_products(),
        'total': cart.get_total_price(),
    }
    return render(request, 'cart/cart_detail.html', context)


@require_POST
@ratelimit('cart', limit=30, period=60)
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    if request.user.is_authenticated and LibraryItem.objects.filter(user=request.user, product=product).exists():
        messages.error(request, 'Ця гра вже є у вашій бібліотеці')
        return redirect(product.get_absolute_url())

    Cart(request).add(product)
    messages.success(request, f'«{product.title}» додано до кошика')
    return redirect(product.get_absolute_url())


@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Cart(request).remove(product)
    messages.info(request, f'«{product.title}» видалено з кошика')
    return redirect('cart:cart_detail')


@require_POST
def cart_clear(request):
    Cart(request).clear()
    messages.info(request, 'Кошик очищено')
    return redirect('cart:cart_detail')


@login_required
@require_POST
@ratelimit('checkout', limit=10, period=60)
def checkout(request):
    cart = Cart(request)
    # ігри, які вже куплені, повторно не купуємо
    owned_ids = LibraryItem.objects.filter(user=request.user).values_list('product_id', flat=True)
    products = list(cart.get_products().exclude(id__in=owned_ids))

    if not products:
        cart.clear()
        messages.error(request, 'Кошик порожній')
        return redirect('cart:cart_detail')

    total = sum(p.final_price() for p in products)

    # transaction.atomic - або все виконається, або нічого (гроші не зникнуть без гри)
    with transaction.atomic():
        # select_for_update блокує рядок профілю поки йде покупка
        profile = UserProfile.objects.select_for_update().get(user=request.user)

        if total > 0 and profile.balance < total:
            need = total - profile.balance
            messages.error(request, f'Недостатньо коштів. Не вистачає {need} USD')
            return redirect(reverse('users:balance') + f'?need={need}')

        profile.balance -= total
        profile.save()

        for product in products:
            LibraryItem.objects.create(user=request.user, product=product, price_paid=product.final_price())

    cart.clear()
    # запам'ятовуємо що купили, щоб показати на сторінці "Дякуємо"
    request.session['last_order'] = [p.id for p in products]
    return redirect('cart:thank_you')


@login_required
def thank_you(request):
    ids = request.session.pop('last_order', None)
    if not ids:
        return redirect('library:library')
    products = Product.objects.filter(id__in=ids)
    return render(request, 'cart/thank_you.html', {'products': products})
