from django.contrib import admin

from .models import Friendship, Message, ChatGroup, GroupMessage, GroupInvite


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_select_related = ['from_user', 'to_user']
    list_display = ['from_user', 'to_user', 'accepted', 'created_at']
    list_filter = ['accepted']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_select_related = ['sender', 'recipient']
    list_display = ['sender', 'recipient', 'text', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']


class GroupMessageInline(admin.TabularInline):
    model = GroupMessage
    extra = 0


@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_select_related = ['owner']
    list_display = ['name', 'owner', 'created_at']
    filter_horizontal = ['members']
    inlines = [GroupMessageInline]


@admin.register(GroupInvite)
class GroupInviteAdmin(admin.ModelAdmin):
    list_select_related = ['group', 'from_user', 'to_user']
    list_display = ['group', 'from_user', 'to_user', 'status', 'created_at']
    list_filter = ['status']
