from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.admin_login_view, name="admin_login"),
    path("logout/", views.admin_logout_view, name="admin_logout"),
    path("dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
    path("forgot-password/", views.admin_forgot_password_view, name="admin_forgot_password"),
    path("forgot-password/otp/", views.admin_forgot_password_otp_view, name="admin_forgot_password_otp"),
    path("forgot-password/resend-otp/", views.admin_forgot_password_resend_otp_view, name="admin_forgot_password_resend_otp"),
    path("forgot-password/reset/", views.admin_forgot_password_reset_view, name="admin_forgot_password_reset"),
    path("users/", views.admin_users_view, name="admin_users"),
    path("users/toggle-block/<int:user_id>/", views.admin_toggle_block_view, name="admin_toggle_block"),
    path("unimplemented/", views.admin_unimplemented_view, name="admin_unimplemented"),
]
