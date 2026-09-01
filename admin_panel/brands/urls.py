from django.urls import path
from . import views

urlpatterns = [
    path('brands/', views.admin_brands_view, name='admin_brands'),
    path('brands/add/', views.add_brand_view, name='add_brand'),
    path('brands/edit/<int:brand_id>/', views.edit_brand_view, name='edit_brand'),
    path('brands/toggle-status/<int:brand_id>/', views.toggle_brand_status_view, name='toggle_brand_status'),
    path('brands/delete/<int:brand_id>/', views.delete_brand_view, name='delete_brand'),
]
