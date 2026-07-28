import re
import time
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.utils import timezone

from .models import User, OTPVerification
from .services import (
    validate_password_strength,
    validate_full_name,
    create_otp,
    send_signup_otp,
    send_reset_otp,
    invalidate_user_sessions,
)

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        fullname         = request.POST.get("fullname", "").strip()
        email            = request.POST.get("email", "").strip().lower()
        mobile_number    = request.POST.get("mobile_number", "").strip()
        referral_code    = request.POST.get("referral_code", "").strip()
        password         = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        error = None

        if not fullname:
            error = "Full name is required."
        else:
            error = validate_full_name(fullname)

        if not error and not email:
            error = "Email is required."
        elif not error:
            try:
                validate_email(email)
            except ValidationError:
                error = "Enter a valid email address."

        if not error:
            if not mobile_number:
                error = "Mobile number is required."
            elif not mobile_number.isdigit():
                error = "Mobile number must contain only digits."
            elif len(mobile_number) != 10:
                error = "Mobile number must be exactly 10 digits."
            elif User.objects.filter(email=email).exists():
                error = "Email already exists"
            elif User.objects.filter(mobile_number=mobile_number).exists():
                error = "Mobile number already exists"
            elif not password:
                error = "Password is required"
            else:
                error = validate_password_strength(password)
                if error is None and password != confirm_password:
                    error = "Passwords do not match"

        if error:
            messages.error(request, error)
            context = {
                "fullname": fullname,
                "email": email,
                "mobile_number": mobile_number,
                "referral_code": referral_code,
            }
            return render(request, "user/authentication/signup.html", context)

        user = User.objects.create_user(
            fullname=fullname,
            email=email,
            mobile_number=mobile_number,
            referral_code=referral_code,
            password=password,
            is_verified=False,
        )

        otp_code, _ = create_otp(user, "signup")
        sent = send_signup_otp(user, otp_code)
        if not sent:
            user.delete()
            messages.error(request, "Failed to send OTP email. Please try again.")
            return render(request, "user/authentication/signup.html", {
                "fullname": fullname,
                "email": email,
                "mobile_number": mobile_number,
                "referral_code": referral_code,
            })

        request.session["pending_user_id"] = user.id
        return redirect("otp_verify")

    return render(request, "user/authentication/signup.html")


def otp_verification_view(request):
    pending_user_id = request.session.get("pending_user_id")
    if not pending_user_id:
        messages.error(request, "Session expired. Please signup again.")
        return redirect("signup")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        try:
            otp_record = OTPVerification.objects.filter(
                user_id=pending_user_id,
                purpose="signup",
                verified=False,
            ).latest("created_at")
        except OTPVerification.DoesNotExist:
            messages.error(request, "OTP not found.")
            return redirect("signup")

        if otp_record.expires_at < timezone.now():
            messages.error(request, "The OTP has expired. Please request a new one.")
            return redirect("otp_verify")

        if entered_otp != otp_record.otp_code:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("otp_verify")

        otp_record.verified = True
        otp_record.save()

        user = User.objects.get(id=pending_user_id)
        user.is_verified = True
        user.save()

        OTPVerification.objects.filter(user=user, purpose="signup").delete()
        request.session.pop("pending_user_id", None)
        request.session.pop("otp_attempts", None)
        request.session.pop("otp_last_sent", None)

        messages.success(request, "Your account has been verified successfully. Please login.")
        return redirect("login")

    return render(request, "user/authentication/otp_verification.html")


def resend_otp_view(request):
    pending_user_id = request.session.get("pending_user_id")
    if not pending_user_id:
        messages.error(request, "Session expired. Please signup again.")
        return redirect("signup")

    if request.method == "POST":
        try:
            user = User.objects.get(id=pending_user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found. Please signup again.")
            return redirect("signup")

        otp_code, _ = create_otp(user, "signup")
        sent = send_signup_otp(user, otp_code)

        if not sent:
            messages.error(request, "Failed to send OTP email. Please try again.")
        else:
            messages.success(request, "A new OTP has been sent to your email.")

        return redirect("otp_verify")

    return redirect("otp_verify")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "user/authentication/login.html", status=400)

        # Check if the user is blocked before checking authenticate to avoid misrepresentation
        try:
            existing_user = User.objects.get(email__iexact=email)
            if existing_user.is_blocked:
                messages.error(request, "Your account has been blocked. Contact support.")
                return render(request, "user/authentication/login.html", status=403)
        except User.DoesNotExist:
            pass

        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "user/authentication/login.html", status=400)

        if not user.is_verified:
            messages.error(request, "Please verify your email before logging in.")
            return render(request, "user/authentication/login.html", status=400)

        if user.is_blocked:
            messages.error(request, "Your account has been blocked. Contact support.")
            return render(request, "user/authentication/login.html", status=403)

        login(request, user)
        return redirect("home")

    return render(request, "user/authentication/login.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "user/authentication/forgot_password.html", status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "This email address is not registered.")
            return render(request, "user/authentication/forgot_password.html", status=400)

        otp_code, _ = create_otp(user, "reset")
        sent = send_reset_otp(user, otp_code)
        if not sent:
            messages.error(request, "Failed to send OTP email. Please try again.")
            return render(request, "user/authentication/forgot_password.html", status=500)

        request.session["reset_user_id"] = user.id
        return redirect("forgot_password_otp")

    return render(request, "user/authentication/forgot_password.html")


def forgot_password_otp_view(request):
    reset_user_id = request.session.get("reset_user_id")
    if not reset_user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("forgot_password")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        try:
            otp_record = OTPVerification.objects.filter(
                user_id=reset_user_id,
                purpose="reset",
                verified=False,
            ).latest("created_at")
        except OTPVerification.DoesNotExist:
            messages.error(request, "OTP not found. Please try again.")
            return redirect("forgot_password")

        if otp_record.expires_at < timezone.now():
            messages.error(request, "The OTP has expired. Please request a new one.")
            return redirect("forgot_password_otp")

        if entered_otp != otp_record.otp_code:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("forgot_password_otp")

        otp_record.verified = True
        otp_record.save()

        OTPVerification.objects.filter(user_id=reset_user_id, purpose="reset").delete()
        request.session["reset_otp_verified"] = True
        return redirect("forgot_password_reset")

    return render(request, "user/authentication/forgot_password_otp.html")


def forgot_password_resend_otp_view(request):
    reset_user_id = request.session.get("reset_user_id")
    if not reset_user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("forgot_password")

    if request.method == "POST":
        try:
            user = User.objects.get(id=reset_user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("forgot_password")

        otp_code, _ = create_otp(user, "reset")
        sent = send_reset_otp(user, otp_code)

        if not sent:
            messages.error(request, "Failed to send OTP email. Please try again.")
        else:
            messages.success(request, "A new OTP has been sent to your email.")

        return redirect("forgot_password_otp")

    return redirect("forgot_password_otp")


def forgot_password_reset_view(request):
    reset_user_id = request.session.get("reset_user_id")
    otp_verified  = request.session.get("reset_otp_verified")

    if not reset_user_id or not otp_verified:
        messages.error(request, "Unauthorized. Please verify your OTP first.")
        return redirect("forgot_password")

    if request.method == "POST":
        new_password     = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not new_password or not confirm_password:
            messages.error(request, "Both fields are required.")
            return render(request, "user/authentication/forgot_password_reset.html", status=400)

        pwd_error = validate_password_strength(new_password)
        if pwd_error:
            messages.error(request, pwd_error)
            return render(request, "user/authentication/forgot_password_reset.html", status=400)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "user/authentication/forgot_password_reset.html", status=400)

        try:
            user = User.objects.get(id=reset_user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("forgot_password")

        user.set_password(new_password)
        user.save()

        invalidate_user_sessions(user)

        request.session.pop("reset_user_id", None)
        request.session.pop("reset_otp_verified", None)
        request.session.pop("reset_attempts", None)
        request.session.pop("reset_last_sent", None)

        return render(request, "user/authentication/forgot_password_reset.html", {
            "password_reset_success": True
        })

    return render(request, "user/authentication/forgot_password_reset.html")


def logout_view(request):
    storage = messages.get_messages(request)
    for _ in storage:
        pass
    storage.used = True

    request.session.pop("pending_user_id", None)
    request.session.pop("reset_user_id", None)
    request.session.pop("reset_otp_verified", None)
    request.session.pop("otp_attempts", None)
    request.session.pop("otp_last_sent", None)
    request.session.pop("reset_attempts", None)
    request.session.pop("reset_last_sent", None)

    logout(request)
    return redirect("login")