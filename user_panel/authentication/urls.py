from django.urls import path
from . import views


urlpatterns = [
	path("signup/", views.signup_view, name="signup"),
	path("otp-verify/", views.otp_verification_view, name="otp_verify"),
	path("resend-otp/", views.resend_otp_view, name="resend_otp"),
	path("login/", views.login_view, name="login"),
	path("forgot-password/", views.forgot_password_view, name="forgot_password"),
	path("forgot-password/otp/", views.forgot_password_otp_view, name="forgot_password_otp"),
	path("forgot-password/resend-otp/", views.forgot_password_resend_otp_view, name="forgot_password_resend_otp"),
	path("forgot-password/reset/", views.forgot_password_reset_view, name="forgot_password_reset"),
	path("logout/", views.logout_view, name="logout"),
]
