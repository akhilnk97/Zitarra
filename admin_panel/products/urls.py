from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.admin_products_view, name='admin_products'),
    path('products/add/', views.admin_product_add_view, name='admin_product_add'),
    path('products/edit/<int:product_id>/', views.admin_product_edit_view, name='admin_product_edit'),
    path('products/delete/<int:product_id>/', views.admin_product_delete_view, name='admin_product_delete'),
    path('products/<int:product_id>/variants/', views.admin_product_variants_view, name='admin_product_variants'),
    path('products/variants/delete/<int:variant_id>/', views.admin_variant_delete_view, name='admin_variant_delete'),
    path('products/variants/toggle/<int:variant_id>/', views.admin_variant_toggle_view, name='admin_variant_toggle'),
    path('products/variants/add/', views.admin_variant_add_select_view, name='admin_variant_add_select'),
]
