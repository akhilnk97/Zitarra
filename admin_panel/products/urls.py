from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.admin_products_view, name='admin_products'),
    path('products/add/', views.admin_product_add_view, name='admin_product_add'),
    path('products/edit/<int:product_id>/', views.admin_product_edit_view, name='admin_product_edit'),
    path('products/delete/<int:product_id>/', views.admin_product_delete_view, name='admin_product_delete'),
]
