from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/place-order/', views.place_order_view, name='place_order'),
    path('checkout/add-address/', views.checkout_add_address_view, name='checkout_add_address'),
    path('checkout/edit-address/<int:address_id>/', views.checkout_edit_address_view, name='checkout_edit_address'),
    path('checkout/success/<str:order_id>/', views.order_success_view, name='order_success'),
    path('orders/', views.my_orders_view, name='my_orders'),
    path('order/<str:order_id>/', views.order_detail_view, name='order_detail'),
    path('order/<str:order_id>/invoice/', views.order_invoice_view, name='order_invoice'),
    path('order/<str:order_id>/cancel/', views.cancel_order_view, name='cancel_order'),
    path('order/<str:order_id>/return/', views.return_order_view, name='return_order'),
]
