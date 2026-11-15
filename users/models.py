from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    # робимо email обов'язковим і унікальним
    email = models.EmailField('Email', unique=True)

    class Meta:
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Користувач',
    )
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True)
    bio = models.TextField('Про себе', blank=True)
    country = models.CharField('Країна', max_length=100, blank=True)
    birth_date = models.DateField('Дата народження', null=True, blank=True)

    # баланс облікового запису, з нього купуються ігри
    balance = models.DecimalField('Баланс (USD)', max_digits=10, decimal_places=2, default=0)
    # коли юзер останній раз щось відкривав на сайті (для статусу онлайн)
    last_seen = models.DateTimeField('Останній раз онлайн', null=True, blank=True)

    class Meta:
        verbose_name = 'Профіль'
        verbose_name_plural = 'Профілі'

    def __str__(self):
        return f'Профіль {self.user.username}'

    def is_online(self):
        if not self.last_seen:
            return False
        return timezone.now() - self.last_seen < timedelta(minutes=5)
