from django.contrib import admin

from .models import LibraryItem, Collection


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    list_select_related = ['user', 'product']
    list_display = ['user', 'product', 'price_paid', 'is_favorite', 'purchased_at']
    list_filter = ['is_favorite', 'purchased_at']
    search_fields = ['user__username', 'product__title']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_select_related = ['user']
    list_display = ['name', 'user', 'created_at']
    filter_horizontal = ['items']
