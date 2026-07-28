from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import cache_control
from django.utils import timezone

from admin_panel.decorators import admin_required
from accounts.models import User, OTPVerification
from accounts.services import create_otp, send_mail_safe, validate_password_strength

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")

    if request.user.is_authenticated and not request.user.is_staff:
        return redirect("home")

    if request.method == "POST":
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "admin_panel/authentication/login.html", status=400)

        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "admin_panel/authentication/login.html", status=400)

        if not user.is_staff:
            messages.error(request, "You do not have admin access.")
            return render(request, "admin_panel/authentication/login.html", status=403)

        if user.is_blocked:
            messages.error(request, "This account has been blocked.")
            return render(request, "admin_panel/authentication/login.html", status=403)

        login(request, user)
        return redirect("admin_dashboard")

    return render(request, "admin_panel/authentication/login.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def admin_forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "admin_panel/authentication/forgot_password.html", status=400)

        try:
            user = User.objects.get(email=email, is_staff=True)
        except User.DoesNotExist:
            messages.error(request, "This email address is not registered as an administrator.")
            return render(request, "admin_panel/authentication/forgot_password.html", status=400)

        otp_code, _ = create_otp(user, "admin_reset")
        subject = "Zitarra Admin — Password Reset Code"
        context = {
            "subject": subject,
            "heading": "Admin Password Reset",
            "user_name": user.fullname,
            "lead_text": "A request was received to reset your Zitarra administrator account password. Use the verification code below to proceed.",
            "otp_code": otp_code,
            "expiry_time": "1 minute",
            "security_warning": True,
        }
        sent = send_mail_safe(
            subject=subject,
            message=None,
            recipient=email,
            html_template="emails/otp_email.html",
            context=context,
        )

        if not sent:
            messages.error(request, "Failed to send email. Please try again.")
            return render(request, "admin_panel/authentication/forgot_password.html", status=500)

        request.session["admin_reset_user_id"] = user.id
        return redirect("admin_forgot_password_otp")

    return render(request, "admin_panel/authentication/forgot_password.html")


def admin_forgot_password_otp_view(request):
    reset_user_id = request.session.get("admin_reset_user_id")
    if not reset_user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("admin_forgot_password")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        try:
            otp_record = OTPVerification.objects.filter(
                user_id=reset_user_id,
                purpose="admin_reset",
                verified=False,
            ).latest("created_at")
        except OTPVerification.DoesNotExist:
            messages.error(request, "OTP not found. Please request a new one.")
            return redirect("admin_forgot_password")

        if otp_record.expires_at < timezone.now():
            messages.error(request, "The OTP has expired. Please request a new one.")
            return redirect("admin_forgot_password_otp")

        if entered_otp != otp_record.otp_code:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("admin_forgot_password_otp")

        otp_record.verified = True
        otp_record.save()

        OTPVerification.objects.filter(user_id=reset_user_id, purpose="admin_reset").delete()
        request.session["admin_reset_otp_verified"] = True
        return redirect("admin_forgot_password_reset")

    return render(request, "admin_panel/authentication/forgot_password_otp.html")


def admin_forgot_password_resend_otp_view(request):
    reset_user_id = request.session.get("admin_reset_user_id")
    if not reset_user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("admin_forgot_password")

    if request.method == "POST":
        try:
            user = User.objects.get(id=reset_user_id)
        except User.DoesNotExist:
            return redirect("admin_forgot_password")

        otp_code, _ = create_otp(user, "admin_reset")
        subject = "Zitarra Admin — New Reset Code"
        context = {
            "subject": subject,
            "heading": "New Admin Reset Code",
            "user_name": user.fullname,
            "lead_text": "Here is your requested new verification code for your Zitarra administrator account password reset.",
            "otp_code": otp_code,
            "expiry_time": "1 minute",
            "security_warning": True,
        }
        send_mail_safe(
            subject=subject,
            message=None,
            recipient=user.email,
            html_template="emails/otp_email.html",
            context=context,
        )
        messages.success(request, "A new code has been sent.")

    return redirect("admin_forgot_password_otp")


def admin_forgot_password_reset_view(request):
    reset_user_id = request.session.get("admin_reset_user_id")
    otp_verified  = request.session.get("admin_reset_otp_verified")

    if not reset_user_id or not otp_verified:
        messages.error(request, "Unauthorized. Please verify your OTP first.")
        return redirect("admin_forgot_password")

    if request.method == "POST":
        new_password     = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not new_password or not confirm_password:
            messages.error(request, "Both fields are required.")
            return render(request, "admin_panel/authentication/forgot_password_reset.html", status=400)

        error = validate_password_strength(new_password)
        if error:
            messages.error(request, error)
            return render(request, "admin_panel/authentication/forgot_password_reset.html", status=400)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "admin_panel/authentication/forgot_password_reset.html", status=400)

        try:
            user = User.objects.get(id=reset_user_id)
        except User.DoesNotExist:
            return redirect("admin_forgot_password")

        user.set_password(new_password)
        user.save()

        request.session.pop("admin_reset_user_id", None)
        request.session.pop("admin_reset_otp_verified", None)
        request.session.pop("admin_reset_attempts", None)
        request.session.pop("admin_reset_last_sent", None)

        messages.success(request, "Password updated successfully. Please login.")
        return redirect("admin_login")

    return render(request, "admin_panel/authentication/forgot_password_reset.html")


def admin_logout_view(request):
    logout(request)
    return redirect("admin_login")
