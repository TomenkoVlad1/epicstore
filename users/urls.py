from django.contrib.auth import views as auth_views
from django.urls import path

from core.ratelimit import ratelimit
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    # не більше 5 спроб входу на хвилину з одного IP (захист від підбору пароля)
    path('login/', ratelimit('login', limit=5, period=60)(auth_views.LoginView.as_view(
        template_name='users/login.html',
        redirect_authenticated_user=True,
    )), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('balance/', views.balance, name='balance'),
]
