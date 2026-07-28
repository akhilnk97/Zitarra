from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.admin_login_view, name="admin_login"),
    path("logout/", views.admin_logout_view, name="admin_logout"),
    path("forgot-password/", views.admin_forgot_password_view, name="admin_forgot_password"),
    path("forgot-password/otp/", views.admin_forgot_password_otp_view, name="admin_forgot_password_otp"),
    path("forgot-password/resend-otp/", views.admin_forgot_password_resend_otp_view, name="admin_forgot_password_resend_otp"),
    path("forgot-password/reset/", views.admin_forgot_password_reset_view, name="admin_forgot_password_reset"),
]
