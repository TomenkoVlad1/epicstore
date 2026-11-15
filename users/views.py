from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import render, redirect

from core.ratelimit import ratelimit
from social.models import Friendship
from social.utils import friends_with_unread, unread_total
from .forms import RegisterForm, UserUpdateForm, ProfileUpdateForm, TopUpForm
from .models import UserProfile


@ratelimit('register', limit=5, period=60 * 10)
def register(request):
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # країну і дату народження зберігає сама форма
            login(request, user)  # одразу логінимо після реєстрації
            messages.success(request, f'Вітаємо, {user.username}! Акаунт створено.')
            return redirect('catalog:home')
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    user = request.user
    friends = friends_with_unread(user)
    # онлайн друзі зверху
    friends.sort(key=lambda x: not x['user'].profile.is_online())

    context = {
        'profile': user.profile,
        'friends': friends,
        'incoming': Friendship.objects.filter(to_user=user, accepted=False).select_related('from_user'),
        'outgoing': Friendship.objects.filter(from_user=user, accepted=False).select_related('to_user'),
        'unread_total': unread_total(user),
        'games_count': user.library_items.count(),
    }
    return render(request, 'users/profile.html', context)


@login_required
def profile_edit(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профіль оновлено')
            return redirect('users:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'users/profile_edit.html', context)


@login_required
@ratelimit('balance', limit=10, period=60)
def balance(request):
    # скільки не вистачає (приходить з оформлення замовлення)
    need = request.GET.get('need')

    if request.method == 'POST':
        form = TopUpForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            # F() - додаємо прямо в базі, щоб не було проблем якщо два запити одночасно
            UserProfile.objects.filter(user=request.user).update(balance=F('balance') + amount)

            # після POST робимо redirect (щоб F5 не поповнив ще раз),
            # а повідомлення про успіх показуємо в тому ж вікні
            request.session['topup_success'] = str(amount)
            request.session['topup_back_to_cart'] = request.POST.get('back') == 'cart'
            return redirect('users:balance')
    else:
        form = TopUpForm(initial={'amount': need} if need else None)

    context = {
        'form': form,
        'need': need,
        'presets': [5, 10, 25, 50, 100],
        # якщо щойно поповнили - показуємо "Платіж успішний"
        'success_amount': request.session.pop('topup_success', None),
        'back_to_cart': request.session.pop('topup_back_to_cart', False),
    }
    return render(request, 'users/balance.html', context)
