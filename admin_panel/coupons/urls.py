from django.urls import path
from . import views

urlpatterns = [
    path('coupons/', views.admin_coupons_list_view, name='admin_coupons'),
    path('coupons/add/', views.admin_add_coupon_view, name='admin_add_coupon'),
    path('coupons/<int:coupon_id>/edit/', views.admin_edit_coupon_view, name='admin_edit_coupon'),
    path('coupons/<int:coupon_id>/delete/', views.admin_delete_coupon_view, name='admin_delete_coupon'),
    path('coupons/<int:coupon_id>/toggle/', views.admin_toggle_coupon_status_view, name='admin_toggle_coupon_status'),
]
