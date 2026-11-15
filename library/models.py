from django.conf import settings
from django.db import models

from catalog.models import Product


class LibraryItem(models.Model):
    """Куплена гра в бібліотеці юзера."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='library_items', verbose_name='Користувач',
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='owners', verbose_name='Гра')
    price_paid = models.DecimalField('Заплачено', max_digits=8, decimal_places=2, default=0)
    is_favorite = models.BooleanField('Улюблена', default=False)
    purchased_at = models.DateTimeField('Дата покупки', auto_now_add=True)

    class Meta:
        verbose_name = 'Гра в бібліотеці'
        verbose_name_plural = 'Ігри в бібліотеках'
        unique_together = ['user', 'product']  # одну гру не можна купити двічі
        ordering = ['-purchased_at']

    def __str__(self):
        return f'{self.user} — {self.product}'


class Collection(models.Model):
    """Своя категорія в бібліотеці (кнопка + біля Усі / Улюблені)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='collections')
    name = models.CharField('Назва', max_length=50)
    items = models.ManyToManyField(LibraryItem, related_name='collections', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Колекція'
        verbose_name_plural = 'Колекції'
        ordering = ['created_at']

    def __str__(self):
        return self.name
