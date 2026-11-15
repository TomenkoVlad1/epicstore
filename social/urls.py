from django.urls import path

from . import views

app_name = 'social'

urlpatterns = [
    path('friends/add/', views.friend_add, name='friend_add'),
    path('friends/<int:pk>/accept/', views.friend_accept, name='friend_accept'),
    path('friends/<int:pk>/decline/', views.friend_decline, name='friend_decline'),
    path('friends/<str:username>/remove/', views.friend_remove, name='friend_remove'),

    path('chats/', views.chats, name='chats'),
    path('chats/dm/<str:username>/', views.dm, name='dm'),

    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:pk>/', views.group_detail, name='group_detail'),
    path('groups/<int:pk>/invite/', views.group_invite, name='group_invite'),
    path('groups/<int:pk>/leave/', views.group_leave, name='group_leave'),
    path('invites/<int:pk>/respond/', views.invite_respond, name='invite_respond'),
]
