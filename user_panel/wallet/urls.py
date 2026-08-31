from django.urls import path
from . import views

urlpatterns = [
    path('wallet/', views.wallet_view, name='user_wallet'),
    path('wallet/add-funds/', views.add_funds_view, name='user_wallet_add_funds'),
    path('wallet/create-razorpay-topup/', views.create_wallet_razorpay_order_view, name='user_wallet_create_razorpay'),
    path('wallet/verify-razorpay-topup/', views.verify_wallet_razorpay_payment_view, name='user_wallet_verify_razorpay'),
]
