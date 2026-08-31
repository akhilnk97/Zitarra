from django.shortcuts import render, redirect
from django.contrib import messages
from common.decorators import user_member_required
from django.http import JsonResponse
from user_panel.authentication.models import User, OTPVerification
from common.services import (
    create_otp,
    send_mail_safe,
    send_password_change_otp,
    send_profile_edit_otp,
    validate_password_strength,
    validate_full_name,
    validate_phone_number,
    validate_pincode,
)
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from .models import Address
from common.services import get_or_create_user_referral_code
from django.core.validators import validate_email
from django.core.exceptions import ValidationError



@user_member_required
def profile_view(request):
    ref_code = get_or_create_user_referral_code(request.user)
    scheme = 'https' if request.is_secure() else 'http'
    domain = request.get_host()
    referral_link = f"{scheme}://{domain}/referral/?ref={ref_code}"
    return render(request, "user/profile/profile.html", {
        'referral_code': ref_code,
        'referral_link': referral_link,
    })


@user_member_required
def profile_send_otp_view(request):
    if request.method != "POST":
        return redirect("profiles:profile_edit")

    fullname = request.POST.get("fullname", "").strip()
    email = request.POST.get("email", "").strip().lower()
    mobile_number = request.POST.get("mobile_number", "").strip() or None

    if not fullname:
        messages.error(request, "Full name is required")
        return render(request, "user/profile/profile_edit.html")
    if not email:
        messages.error(request, "Email is required")
        return render(request, "user/profile/profile_edit.html")

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Enter a valid email address.")
        return render(request, "user/profile/profile_edit.html")

    if request.user.socialaccount_set.exists() and email != request.user.email.lower():
        messages.error(request, "Google authenticated users cannot change their email address.")
        return render(request, "user/profile/profile_edit.html")

    if mobile_number:
        if not mobile_number.isdigit():
            messages.error(request, "Mobile number must contain only digits.")
            return render(request, "user/profile/profile_edit.html")
        if len(mobile_number) != 10:
            messages.error(request, "Mobile number must be 10 digits.")
            return render(request, "user/profile/profile_edit.html")

    if User.objects.filter(email__iexact=email).exclude(id=request.user.id).exists():
        messages.error(request, "This email address is already in use")
        return render(request, "user/profile/profile_edit.html")

    if mobile_number and User.objects.filter(mobile_number=mobile_number).exclude(id=request.user.id).exists():
        messages.error(request, "This phone number is already in use")
        return render(request, "user/profile/profile_edit.html")

    if request.FILES.get("profile_image"):
        request.user.profile_image = request.FILES["profile_image"]
        request.user.save()

    request.session["pending_profile_update"] = {
        "fullname": fullname,
        "email": email,
        "mobile_number": mobile_number
    }

    if not send_profile_edit_otp(request.user, email):
        messages.error(request, "Failed to send OTP email. Please try again.")
        return render(request, "user/profile/profile_edit.html")

    is_resend = request.POST.get("is_resend") == "true"
    if is_resend:
        messages.info(request, "An OTP verification code has been sent to your email.", extra_tags='otp_info')
    pending = request.session.get("pending_profile_update")
    return render(request, "user/profile/profile_edit.html", {"show_otp_modal": True, "otp_sent": True, "pending_data": pending})


@user_member_required
def profile_edit_view(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        
        if entered_otp:
            pending_data = request.session.get("pending_profile_update")
            if not pending_data:
                messages.error(request, "Session expired or invalid update request. Please try again.")
                return render(request, "user/profile/profile_edit.html")

            try:
                otp_record = OTPVerification.objects.filter(
                    user=request.user,
                    purpose="profile_edit",
                    verified=False
                ).latest('created_at')
                is_expired = otp_record.expires_at < timezone.now()
            except OTPVerification.DoesNotExist:
                messages.error(request, "OTP not found. Please request a new code.", extra_tags='otp_error')
                return render(request, "user/profile/profile_edit.html", {"show_otp_modal": True, "otp_expired": True, "pending_data": pending_data})

            if entered_otp != otp_record.otp_code:
                messages.error(request, "Invalid OTP. Please try again.", extra_tags='otp_error')
                return render(request, "user/profile/profile_edit.html", {"show_otp_modal": True, "otp_expired": is_expired, "pending_data": pending_data})

            if otp_record.expires_at < timezone.now():
                messages.error(request, "OTP has expired. Please request a new code.", extra_tags='otp_error')
                return render(request, "user/profile/profile_edit.html", {"show_otp_modal": True, "otp_expired": True, "pending_data": pending_data})

            if request.user.socialaccount_set.exists() and pending_data["email"] != request.user.email.lower():
                messages.error(request, "Google authenticated users cannot change their email address.")
                return render(request, "user/profile/profile_edit.html")

            request.user.fullname = pending_data["fullname"]
            request.user.email = pending_data["email"]
            request.user.mobile_number = pending_data["mobile_number"] or None
            
            if request.FILES.get("profile_image"):
                request.user.profile_image = request.FILES["profile_image"]
                
            request.user.save()

            otp_record.verified = True
            otp_record.save()
            OTPVerification.objects.filter(user=request.user, purpose="profile_edit").delete()
            request.session.pop("pending_profile_update", None)

            return redirect("/profile/?success=1")

        fullname = request.POST.get("fullname", "").strip()
        if not fullname:
            messages.error(request, "Full name is required.")
            return render(request, "user/profile/profile_edit.html")

        request.user.fullname = fullname
        if request.FILES.get("profile_image"):
            request.user.profile_image = request.FILES["profile_image"]
        request.user.save()

        return redirect("/profile/?success=1")

    return render(request, "user/profile/profile_edit.html")


@user_member_required
def addresses_view(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, "user/profile/addresses.html", {"addresses": addresses})


@user_member_required
def address_save_view(request):
    if request.method != "POST":
        return redirect("addresses")

    address_id     = request.POST.get("id", "").strip()
    full_name      = request.POST.get("full_name", "").strip().upper()
    phone_number   = request.POST.get("phone_number", "").strip().upper()
    address_line_1 = request.POST.get("address_line_1", "").strip().upper()
    address_line_2 = request.POST.get("address_line_2", "").strip().upper()
    city           = request.POST.get("city", "").strip().upper()
    state          = request.POST.get("state", "").strip().upper()
    pincode        = request.POST.get("pincode", "").strip().upper()
    badge          = request.POST.get("badge", "").strip().upper()
    is_default     = request.POST.get("is_default") in ["true", "on"]
    label          = request.POST.get("label", "HOME").strip().upper()

    if not full_name or not phone_number or not address_line_1 or not city or not state or not pincode:
        messages.error(request, "All required fields must be filled.")
        return redirect("addresses")

    error = validate_full_name(full_name) or validate_phone_number(phone_number) or validate_pincode(pincode)
    if error:
        messages.error(request, error)
        return redirect("addresses")

    badge_val = "DEFAULT" if is_default else (badge if badge != "DEFAULT" else "")

    if address_id:
        try:
            addr = Address.objects.get(id=address_id, user=request.user)
            addr.full_name      = full_name
            addr.phone_number   = phone_number
            addr.address_line_1 = address_line_1
            addr.address_line_2 = address_line_2 or None
            addr.city           = city
            addr.state          = state
            addr.pincode        = pincode
            addr.is_default     = is_default
            addr.badge          = badge_val
            addr.label          = label
            addr.save()
            messages.success(request, "Address updated successfully!")
        except Address.DoesNotExist:
            messages.error(request, "Address record not found.")
    else:
        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone_number,
            address_line_1=address_line_1,
            address_line_2=address_line_2 or None,
            city=city,
            state=state,
            pincode=pincode,
            is_default=is_default,
            badge=badge_val,
            label=label
        )
        messages.success(request, "Address created successfully!")

    return redirect("addresses")


@user_member_required
def address_delete_view(request, address_id):
    if request.method != "POST":
        return redirect("addresses")

    try:
        address = Address.objects.get(id=address_id, user=request.user)
    except Address.DoesNotExist:
        messages.error(request, "Address not found.")
        return redirect("addresses")

    was_default = address.is_default
    address.delete()

    if was_default:
        next_address = Address.objects.filter(user=request.user).first()
        if next_address:
            next_address.is_default = True
            next_address.badge = 'DEFAULT'
            next_address.save()

    messages.success(request, "Address deleted successfully!")
    return redirect("addresses")


@user_member_required
def profile_password_send_otp_view(request):
    if request.user.socialaccount_set.exists():
        messages.error(request, "Social authenticated users cannot change their password.")
        return redirect("profiles:profile")

    if request.method != "POST":
        return redirect("profiles:profile_password")

    current_pwd = request.POST.get("current_pwd", "").strip()
    new_pwd     = request.POST.get("new_pwd", "").strip()
    confirm_pwd = request.POST.get("confirm_pwd", "").strip()

    context = {
        "current_pwd": current_pwd,
        "new_pwd": new_pwd,
        "confirm_pwd": confirm_pwd
    }

    if not current_pwd or not request.user.check_password(current_pwd):
        messages.error(request, "Incorrect current password.")
        return render(request, "user/profile/password.html", context)

    if current_pwd == new_pwd:
        messages.error(request, "New password cannot be the same as current password.")
        return render(request, "user/profile/password.html", context)

    if not new_pwd or new_pwd != confirm_pwd:
        messages.error(request, "New passwords do not match or are empty.")
        return render(request, "user/profile/password.html", context)

    strength_error = validate_password_strength(new_pwd)
    if strength_error:
        messages.error(request, strength_error)
        return render(request, "user/profile/password.html", context)

    if not send_password_change_otp(request.user):
        messages.error(request, "Failed to send OTP email. Please try again.")
        return render(request, "user/profile/password.html", context)

    is_resend = request.POST.get("is_resend") == "true"
    if is_resend:
        messages.info(request, "An OTP verification code has been sent to your email.", extra_tags='otp_info')
    
    context.update({"show_otp_modal": True, "otp_sent": True})
    return render(request, "user/profile/password.html", context)


@user_member_required
def profile_password_view(request):

    if request.user.socialaccount_set.exists():
        if request.method == "POST":
            messages.error(request, "Social authenticated users cannot change their password.")
        return redirect('profiles:profile')

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        current_pwd = request.POST.get("current_pwd", "").strip()
        new_pwd     = request.POST.get("new_pwd", "").strip()
        confirm_pwd = request.POST.get("confirm_pwd", "").strip()

        context = {
            "current_pwd": current_pwd,
            "new_pwd": new_pwd,
            "confirm_pwd": confirm_pwd
        }

        try:
            otp_record = OTPVerification.objects.filter(
                user=request.user, purpose="password_change", verified=False
            ).latest('created_at')
            is_expired = otp_record.expires_at < timezone.now()
        except OTPVerification.DoesNotExist:
            messages.error(request, "OTP not found. Please request a new code.", extra_tags='otp_error')
            context.update({"show_otp_modal": True, "otp_expired": True})
            return render(request, "user/profile/password.html", context)

        if not entered_otp or entered_otp != otp_record.otp_code:
            messages.error(request, "Invalid OTP code. Please try again.", extra_tags='otp_error')
            context.update({"show_otp_modal": True, "otp_expired": is_expired})
            return render(request, "user/profile/password.html", context)

        if otp_record.expires_at < timezone.now():
            messages.error(request, "OTP has expired. Please request a new code.", extra_tags='otp_error')
            context.update({"show_otp_modal": True, "otp_expired": True})
            return render(request, "user/profile/password.html", context)

        if not current_pwd or not request.user.check_password(current_pwd):
            messages.error(request, "Incorrect current password.")
            return render(request, "user/profile/password.html", context)

        if current_pwd == new_pwd:
            messages.error(request, "New password cannot be the same as current password.")
            return render(request, "user/profile/password.html", context)

        if not new_pwd or new_pwd != confirm_pwd:
            messages.error(request, "New passwords do not match or are empty.")
            return render(request, "user/profile/password.html", context)

        strength_error = validate_password_strength(new_pwd)
        if strength_error:
            messages.error(request, strength_error)
            return render(request, "user/profile/password.html", context)

        request.user.set_password(new_pwd)
        request.user.save()

        OTPVerification.objects.filter(user=request.user, purpose="password_change").delete()
        update_session_auth_hash(request, request.user)

        messages.success(request, "Password updated successfully!")
        return redirect("profiles:profile_password")

    return render(request, "user/profile/password.html")
