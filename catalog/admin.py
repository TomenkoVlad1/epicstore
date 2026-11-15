from django.contrib import admin
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_select_related = ['category']
    list_display = ['title', 'category', 'price', 'discount_price', 'release_date', 'is_featured', 'is_active']
    list_filter = ['category', 'is_active', 'is_featured', 'release_date', 'developer']
    list_editable = ['price', 'discount_price', 'is_featured', 'is_active']
    search_fields = ['title', 'developer', 'publisher']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline]
