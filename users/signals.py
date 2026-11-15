from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser, UserProfile


@receiver(post_save, sender=CustomUser)
def create_profile(sender, instance, created, **kwargs):
    # коли зареєструвався новий юзер - одразу створюємо йому профіль
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_profile(sender, instance, **kwargs):
    # на випадок якщо профілю чомусь нема (наприклад старий юзер)
    UserProfile.objects.get_or_create(user=instance)


# ---- повідомлення при вході / виході ----
# fail_silently=True - бо при вході з тестів або адмінки може не бути сховища повідомлень

@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    # після реєстрації вже є своє повідомлення "Акаунт створено"
    if request is not None and not request.path.endswith('/register/'):
        messages.success(request, f'Ви увійшли як {user.username}', fail_silently=True)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if request is not None:
        messages.info(request, 'Ви вийшли з акаунта', fail_silently=True)
