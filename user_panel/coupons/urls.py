from django.urls import path
from . import views

urlpatterns = [
    path('checkout/apply-coupon/', views.apply_coupon_view, name='apply_coupon'),
    path('checkout/remove-coupon/', views.remove_coupon_view, name='remove_coupon'),
    path('referral/', views.referral_landing_view, name='referral_landing'),
    path('my-referrals/', views.user_referrals_view, name='user_referrals'),
]
