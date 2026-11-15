from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from catalog.cache import invalidate_catalog
from .models import News


@receiver([post_save, post_delete], sender=News)
def clear_cache_on_news(sender, **kwargs):
    # новини показуються на головній, тому теж скидаємо кеш
    invalidate_catalog()
