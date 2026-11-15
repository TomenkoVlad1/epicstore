from django.contrib import admin

from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_select_related = ['product']
    list_display = ['title', 'product', 'is_published', 'created_at']
    list_filter = ['is_published', 'created_at']
    list_editable = ['is_published']
    search_fields = ['title', 'text']
    prepopulated_fields = {'slug': ('title',)}
