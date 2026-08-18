from django.urls import path
from . import views

urlpatterns = [
    path('orders/', views.admin_orders_view, name='admin_orders'),
    path('orders/<str:order_id>/', views.admin_order_detail_view, name='admin_order_detail'),
    path('orders/<str:order_id>/update-status/', views.admin_order_update_status_view, name='admin_order_update_status'),
]
