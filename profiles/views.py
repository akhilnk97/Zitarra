from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from accounts.decorators import user_not_blocked
from django.http import JsonResponse
from accounts.models import User, OTPVerification
from accounts.services import create_otp, send_mail_safe, validate_password_strength
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
import json
from .models import Address


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_view(request):
    return render(request, "user/profile/profile.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_send_otp_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    fullname = request.POST.get("fullname", "").strip()
    email = request.POST.get("email", "").strip().lower()
    mobile_number = request.POST.get("mobile_number", "").strip() or None

    if not fullname:
        return JsonResponse({"status": "error", "message": "Full name is required"}, status=400)
    if not email:
        return JsonResponse({"status": "error", "message": "Email is required"}, status=400)

    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"status": "error", "message": "Enter a valid email address."}, status=400)

    if request.user.socialaccount_set.exists() and email != request.user.email.lower():
        return JsonResponse({"status": "error", "message": "Google authenticated users cannot change their email address."}, status=400)

    if mobile_number:
        if not mobile_number.isdigit():
            return JsonResponse({"status": "error", "message": "Mobile number must contain only digits."}, status=400)
        if len(mobile_number) != 10:
            return JsonResponse({"status": "error", "message": "Mobile number must be 10 digits."}, status=400)

    if User.objects.filter(email__iexact=email).exclude(id=request.user.id).exists():
        return JsonResponse({"status": "error", "message": "This email address is already in use"}, status=400)

    if mobile_number and User.objects.filter(mobile_number=mobile_number).exclude(id=request.user.id).exists():
        return JsonResponse({"status": "error", "message": "This phone number is already in use"}, status=400)

    request.session["pending_profile_update"] = {
        "fullname": fullname,
        "email": email,
        "mobile_number": mobile_number
    }

    otp_code, _ = create_otp(request.user, "profile_edit")
    subject = "Zitarra — Profile Update Verification Code"
    message = f"Hello {request.user.fullname},\n\nYour profile update verification OTP is:\n\n{otp_code}\n\nThis code is valid for 1 minute.\n\nThank You,\nZitarra Team"
    
    sent = send_mail_safe(subject, message, email)
    if not sent:
        return JsonResponse({"status": "error", "message": "Failed to send OTP email. Please try again."}, status=500)

    return JsonResponse({"status": "success"})


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_edit_view(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        
        if entered_otp:
            pending_data = request.session.get("pending_profile_update")
            if not pending_data:
                return JsonResponse({"status": "error", "message": "Session expired or invalid update request. Please try again."}, status=400)

            try:
                otp_record = OTPVerification.objects.filter(
                    user=request.user,
                    purpose="profile_edit",
                    verified=False
                ).latest('created_at')
            except OTPVerification.DoesNotExist:
                return JsonResponse({"status": "error", "message": "OTP not found. Please request a new code."}, status=400)

            if otp_record.expires_at < timezone.now():
                return JsonResponse({"status": "error", "message": "OTP has expired. Please request a new code."}, status=400)

            if entered_otp != otp_record.otp_code:
                return JsonResponse({"status": "error", "message": "Invalid OTP. Please try again."}, status=400)

            if request.user.socialaccount_set.exists() and pending_data["email"] != request.user.email.lower():
                return JsonResponse({"status": "error", "message": "Google authenticated users cannot change their email address."}, status=400)

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

            return JsonResponse({"status": "success"})

        else:
            fullname = request.POST.get("fullname", "").strip()
            email = request.POST.get("email", "").strip().lower()
            mobile_number = request.POST.get("mobile_number", "").strip()

            current_phone = request.user.mobile_number or ""
            if email != request.user.email.lower() or mobile_number != current_phone:
                return JsonResponse({"status": "error", "message": "OTP verification is required to change email or phone number."}, status=400)

            if not fullname:
                return JsonResponse({"status": "error", "message": "Full name is required"}, status=400)

            request.user.fullname = fullname
            if request.FILES.get("profile_image"):
                request.user.profile_image = request.FILES["profile_image"]
            request.user.save()

            return JsonResponse({"status": "success"})

    return render(request, "user/profile/profile_edit.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def addresses_view(request):
    addresses = Address.objects.filter(user=request.user)
    addresses_data = []
    for addr in addresses:
        addresses_data.append({
            "id": str(addr.id),
            "badge": addr.badge or "",
            "is_default": addr.is_default,
            "full_name": addr.full_name,
            "phone_number": addr.phone_number,
            "address_line_1": addr.address_line_1,
            "address_line_2": addr.address_line_2 or "",
            "city": addr.city,
            "state": addr.state,
            "pincode": addr.pincode,
            "label": addr.label
        })
    addresses_json = json.dumps(addresses_data)
    return render(request, "user/profile/addresses.html", {"addresses_json": addresses_json})


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def addresses_api_list_view(request):
    addresses = Address.objects.filter(user=request.user)
    addresses_data = []
    for addr in addresses:
        addresses_data.append({
            "id": str(addr.id),
            "badge": addr.badge or "",
            "is_default": addr.is_default,
            "full_name": addr.full_name,
            "phone_number": addr.phone_number,
            "address_line_1": addr.address_line_1,
            "address_line_2": addr.address_line_2 or "",
            "city": addr.city,
            "state": addr.state,
            "pincode": addr.pincode,
            "label": addr.label
        })
    return JsonResponse(addresses_data, safe=False)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def address_save_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    address_id = request.POST.get("id", "").strip()
    raw_fullname = request.POST.get("full_name", "")
    full_name = raw_fullname.strip().upper()
    raw_phone = request.POST.get("phone_number", "")
    phone_number = raw_phone.strip().upper()
    raw_line1 = request.POST.get("address_line_1", "")
    address_line_1 = raw_line1.strip().upper()
    address_line_2 = request.POST.get("address_line_2", "").strip().upper()
    raw_city = request.POST.get("city", "")
    city = raw_city.strip().upper()
    raw_state = request.POST.get("state", "")
    state = raw_state.strip().upper()
    raw_pincode = request.POST.get("pincode", "")
    pincode = raw_pincode.strip().upper()
    badge = request.POST.get("badge", "").strip().upper()
    is_default = request.POST.get("is_default") == "true"
    label = request.POST.get("label", "HOME").strip().upper()

    if not full_name or not phone_number or not address_line_1 or not city or not state or not pincode:
        return JsonResponse({"status": "error", "message": "All fields (Full Name, Phone Number, Address Line 1, City, State, and Pincode) are required."}, status=400)

    import re

    # Recipient Name Validation
    if raw_fullname.startswith(" "):
        return JsonResponse({"status": "error", "message": "Recipient name cannot start with a space."}, status=400)
    if not full_name:
        return JsonResponse({"status": "error", "message": "Recipient name is required."}, status=400)
    if len(full_name) < 3:
        return JsonResponse({"status": "error", "message": "Recipient name must be at least 3 characters."}, status=400)
    if not re.match(r'^[A-Z]+( [A-Z]+)*$', full_name):
        if any(char.isdigit() for char in full_name):
            return JsonResponse({"status": "error", "message": "Recipient name cannot contain numbers."}, status=400)
        elif any(not char.isalnum() and not char.isspace() for char in full_name):
            return JsonResponse({"status": "error", "message": "Recipient name cannot contain special characters."}, status=400)
        elif "  " in raw_fullname:
            return JsonResponse({"status": "error", "message": "Recipient name cannot contain consecutive spaces."}, status=400)
        else:
            return JsonResponse({"status": "error", "message": "Please enter a valid recipient name (letters and single spaces only)."}, status=400)

    # Phone Number Validation
    if raw_phone.startswith(" "):
        return JsonResponse({"status": "error", "message": "Phone number cannot start with a space."}, status=400)
    if not re.match(r'^\d{10}$', phone_number):
        if not phone_number.isdigit():
            return JsonResponse({"status": "error", "message": "Phone number must contain only digits."}, status=400)
        else:
            return JsonResponse({"status": "error", "message": "Phone number must be exactly 10 digits."}, status=400)

    # Pincode Validation
    if raw_pincode.startswith(" "):
        return JsonResponse({"status": "error", "message": "Pincode cannot start with a space."}, status=400)
    if not re.match(r'^\d{6}$', pincode):
        if not pincode.isdigit():
            return JsonResponse({"status": "error", "message": "Pincode must contain only digits."}, status=400)
        else:
            return JsonResponse({"status": "error", "message": "Pincode must be exactly 6 digits."}, status=400)

    # City & State Validation
    if raw_city.startswith(" "):
        return JsonResponse({"status": "error", "message": "City cannot start with a space."}, status=400)
    if not re.match(r'^[A-Z\s.-]+$', city):
        return JsonResponse({"status": "error", "message": "City must contain only letters."}, status=400)

    if raw_state.startswith(" "):
        return JsonResponse({"status": "error", "message": "State cannot start with a space."}, status=400)
    if not re.match(r'^[A-Z\s.-]+$', state):
        return JsonResponse({"status": "error", "message": "State must contain only letters."}, status=400)

    # Line 1 Validation
    if raw_line1.startswith(" "):
        return JsonResponse({"status": "error", "message": "Address Line 1 cannot start with a space."}, status=400)

    if address_id:
        try:
            addr = Address.objects.get(id=address_id, user=request.user)
            addr.full_name = full_name
            addr.phone_number = phone_number
            addr.address_line_1 = address_line_1
            addr.address_line_2 = address_line_2 or None
            addr.city = city
            addr.state = state
            addr.pincode = pincode
            addr.is_default = is_default
            addr.label = label
            if is_default:
                addr.badge = "DEFAULT"
            else:
                addr.badge = badge if badge != "DEFAULT" else ""
            addr.save()
            return JsonResponse({"status": "success", "message": "Location record updated successfully"})
        except Address.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Address not found"}, status=404)
    else:
        addr = Address(
            user=request.user,
            full_name=full_name,
            phone_number=phone_number,
            address_line_1=address_line_1,
            address_line_2=address_line_2 or None,
            city=city,
            state=state,
            pincode=pincode,
            is_default=is_default,
            label=label,
            badge="DEFAULT" if is_default else badge
        )
        addr.save()
        return JsonResponse({"status": "success", "message": "Location record created successfully", "id": str(addr.id)}, status=201)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def address_delete_view(request, address_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        addr = Address.objects.get(id=address_id, user=request.user)
        is_deleted_default = addr.is_default
        addr.delete()

        if is_deleted_default:
            first_remaining = Address.objects.filter(user=request.user).first()
            if first_remaining:
                first_remaining.is_default = True
                first_remaining.badge = 'DEFAULT'
                first_remaining.save()

        return JsonResponse({"status": "success", "message": "Location record deleted successfully"})
    except Address.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Address not found"}, status=404)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_password_send_otp_view(request):
    if request.user.socialaccount_set.exists():
        return JsonResponse({"status": "error", "message": "Social authenticated users cannot change their password."}, status=400)

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    current_pwd = request.POST.get("current_pwd", "").strip()
    new_pwd = request.POST.get("new_pwd", "").strip()
    confirm_pwd = request.POST.get("confirm_pwd", "").strip()

    if not current_pwd:
        return JsonResponse({"status": "error", "field": "current_pwd", "message": "Current password is required."}, status=400)
    
    if not request.user.check_password(current_pwd):
        return JsonResponse({"status": "error", "field": "current_pwd", "message": "Incorrect current password."}, status=400)

    if not new_pwd:
        return JsonResponse({"status": "error", "field": "new_pwd", "message": "New password is required."}, status=400)

    strength_error = validate_password_strength(new_pwd)
    if strength_error:
        return JsonResponse({"status": "error", "field": "new_pwd", "message": strength_error}, status=400)

    if new_pwd != confirm_pwd:
        return JsonResponse({"status": "error", "field": "confirm_pwd", "message": "Passwords do not match."}, status=400)

    otp_code, _ = create_otp(request.user, "password_change")
    subject = "Zitarra — Password Change Verification Code"
    message = f"Hello {request.user.fullname},\n\nYour password change verification OTP is:\n\n{otp_code}\n\nThis code is valid for 1 minute.\n\nThank You,\nZitarra Team"
    
    sent = send_mail_safe(subject, message, request.user.email)
    if not sent:
        return JsonResponse({"status": "error", "message": "Failed to send OTP email. Please try again."}, status=500)

    return JsonResponse({"status": "success"})


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_password_view(request):
    is_social = request.user.socialaccount_set.exists()
    if is_social:
        if request.method == "POST":
            return JsonResponse({"status": "error", "message": "Social authenticated users cannot change their password."}, status=400)
        return redirect('profiles:profile')

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        current_pwd = request.POST.get("current_pwd", "").strip()
        new_pwd = request.POST.get("new_pwd", "").strip()

        if not entered_otp:
            return JsonResponse({"status": "error", "message": "OTP code is required."}, status=400)

        try:
            otp_record = OTPVerification.objects.filter(
                user=request.user,
                purpose="password_change",
                verified=False
            ).latest('created_at')
        except OTPVerification.DoesNotExist:
            return JsonResponse({"status": "error", "message": "OTP not found. Please request a new code."}, status=400)

        if otp_record.expires_at < timezone.now():
            return JsonResponse({"status": "error", "message": "OTP has expired. Please request a new code."}, status=400)

        if entered_otp != otp_record.otp_code:
            return JsonResponse({"status": "error", "message": "Invalid OTP. Please try again."}, status=400)

        if not current_pwd or not request.user.check_password(current_pwd):
            return JsonResponse({"status": "error", "message": "Current password verification failed."}, status=400)

        strength_error = validate_password_strength(new_pwd)
        if strength_error:
            return JsonResponse({"status": "error", "message": strength_error}, status=400)

        request.user.set_password(new_pwd)
        request.user.save()

        update_session_auth_hash(request, request.user)

        otp_record.verified = True
        otp_record.save()
        OTPVerification.objects.filter(user=request.user, purpose="password_change").delete()

        return JsonResponse({"status": "success"})

    return render(request, "user/profile/password.html")
