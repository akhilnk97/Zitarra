from django.urls import path
from . import views

urlpatterns = [
    path('banners/', views.admin_banners_view, name='admin_banners'),
    path('banners/add/', views.add_banner_view, name='add_banner'),
    path('banners/edit/<int:banner_id>/', views.edit_banner_view, name='edit_banner'),
    path('banners/toggle-status/<int:banner_id>/', views.toggle_banner_status_view, name='toggle_banner_status'),
    path('banners/delete/<int:banner_id>/', views.delete_banner_view, name='delete_banner'),
    path('banners/showcases/', views.admin_showcases_view, name='admin_showcases'),
    path('banners/showcases/edit/<int:showcase_id>/', views.edit_showcase_view, name='edit_showcase'),
]
