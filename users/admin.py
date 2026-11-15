from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email']
    inlines = [UserProfileInline]

    # email додав, бо він в мене обов'язковий
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        # при створенні юзера профіль робить сигнал, тому inline тільки при редагуванні
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_select_related = ['user']
    list_display = ['user', 'country', 'birth_date']
    search_fields = ['user__username', 'country']
