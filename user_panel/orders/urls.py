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
    path('order/<str:order_id>/item/<int:item_id>/cancel/', views.cancel_order_item_view, name='cancel_order_item'),
    path('checkout/create-razorpay-order/', views.create_razorpay_order_view, name='create_razorpay_order'),
    path('checkout/verify-razorpay-payment/', views.verify_razorpay_payment_view, name='verify_razorpay_payment'),
    path('checkout/payment-failed/', views.payment_failed_view, name='payment_failed'),
    path('checkout/retry-payment/', views.retry_payment_view, name='retry_payment'),
]

