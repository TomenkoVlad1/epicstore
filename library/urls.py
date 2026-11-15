from django.urls import path

from . import views

app_name = 'library'

urlpatterns = [
    path('', views.library, name='library'),
    path('item/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('collections/create/', views.collection_create, name='collection_create'),
    path('collections/<int:pk>/delete/', views.collection_delete, name='collection_delete'),
    path('collections/<int:pk>/toggle/<int:item_id>/', views.collection_toggle, name='collection_toggle'),
]
