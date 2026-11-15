from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.home, name='home'),                      # Цікавинки
    path('browse/', views.product_list, name='product_list'),  # Всеогляд
    path('game/<slug:slug>/', views.product_detail, name='product_detail'),
]
