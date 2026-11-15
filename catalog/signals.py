from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .cache import invalidate_catalog
from .models import Category, Product, ProductImage


@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=ProductImage)
def clear_catalog_cache(sender, **kwargs):
    # будь-яка зміна в каталозі - скидаємо кеш
    invalidate_catalog()
