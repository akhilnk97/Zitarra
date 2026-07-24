from django.shortcuts import render, redirect
<<<<<<< HEAD
=======
from django.contrib import messages
>>>>>>> 8e77622 (Refactored the user input validation)
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from accounts.decorators import user_not_blocked
from django.http import JsonResponse
from accounts.models import User, OTPVerification
<<<<<<< HEAD
from accounts.services import create_otp, send_mail_safe, validate_password_strength
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
import json
=======
from accounts.services import (
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
import re
>>>>>>> 8e77622 (Refactored the user input validation)
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
<<<<<<< HEAD
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
=======
        return redirect("profiles:profile_edit")
>>>>>>> 8e77622 (Refactored the user input validation)

    fullname = request.POST.get("fullname", "").strip()
    email = request.POST.get("email", "").strip().lower()
    mobile_number = request.POST.get("mobile_number", "").strip() or None

    if not fullname:
<<<<<<< HEAD
        return JsonResponse({"status": "error", "message": "Full name is required"}, status=400)
    if not email:
        return JsonResponse({"status": "error", "message": "Email is required"}, status=400)
=======
        messages.error(request, "Full name is required")
        return render(request, "user/profile/profile_edit.html")
    if not email:
        messages.error(request, "Email is required")
        return render(request, "user/profile/profile_edit.html")
>>>>>>> 8e77622 (Refactored the user input validation)

    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
    except ValidationError:
<<<<<<< HEAD
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
=======
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
>>>>>>> 8e77622 (Refactored the user input validation)

    request.session["pending_profile_update"] = {
        "fullname": fullname,
        "email": email,
        "mobile_number": mobile_number
    }

<<<<<<< HEAD
    otp_code, _ = create_otp(request.user, "profile_edit")
    subject = "Zitarra — Profile Update Verification Code"
    message = f"Hello {request.user.fullname},\n\nYour profile update verification OTP is:\n\n{otp_code}\n\nThis code is valid for 1 minute.\n\nThank You,\nZitarra Team"
    
    sent = send_mail_safe(subject, message, email)
    if not sent:
        return JsonResponse({"status": "error", "message": "Failed to send OTP email. Please try again."}, status=500)

    return JsonResponse({"status": "success"})
=======
    if not send_profile_edit_otp(request.user, email):
        messages.error(request, "Failed to send OTP email. Please try again.")
        return render(request, "user/profile/profile_edit.html")

    return render(request, "user/profile/profile_edit.html", {"show_otp_modal": True})


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_resend_otp_view(request):
    if request.method != "POST":
        return redirect("profiles:profile_edit")

    pending_data = request.session.get("pending_profile_update")
    if not pending_data:
        messages.error(request, "Session expired. Please update your profile again.")
        return redirect("profiles:profile_edit")

    email = pending_data["email"]
    if not send_profile_edit_otp(request.user, email):
        return render(request, "user/profile/profile_edit.html", {
            "show_otp_modal": True,
            "otp_error": "Failed to resend OTP. Please try again."
        })

    return render(request, "user/profile/profile_edit.html", {
        "show_otp_modal": True,
        "otp_success": "A new OTP verification code has been sent to your email."
    })
>>>>>>> 8e77622 (Refactored the user input validation)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_edit_view(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        
<<<<<<< HEAD
        if entered_otp:
            pending_data = request.session.get("pending_profile_update")
            if not pending_data:
                return JsonResponse({"status": "error", "message": "Session expired or invalid update request. Please try again."}, status=400)
=======
        # 1. User submitted OTP -> Verify OTP and save Email/Mobile changes
        if entered_otp:
            pending_data = request.session.get("pending_profile_update")
            if not pending_data:
                messages.error(request, "Session expired or invalid update request. Please try again.")
                return render(request, "user/profile/profile_edit.html")
>>>>>>> 8e77622 (Refactored the user input validation)

            try:
                otp_record = OTPVerification.objects.filter(
                    user=request.user,
                    purpose="profile_edit",
                    verified=False
                ).latest('created_at')
            except OTPVerification.DoesNotExist:
<<<<<<< HEAD
                return JsonResponse({"status": "error", "message": "OTP not found. Please request a new code."}, status=400)

            if otp_record.expires_at < timezone.now():
                return JsonResponse({"status": "error", "message": "OTP has expired. Please request a new code."}, status=400)

            if entered_otp != otp_record.otp_code:
                return JsonResponse({"status": "error", "message": "Invalid OTP. Please try again."}, status=400)

            if request.user.socialaccount_set.exists() and pending_data["email"] != request.user.email.lower():
                return JsonResponse({"status": "error", "message": "Google authenticated users cannot change their email address."}, status=400)
=======
                return render(request, "user/profile/profile_edit.html", {
                    "show_otp_modal": True,
                    "otp_error": "OTP not found. Please request a new code."
                })

            if entered_otp != otp_record.otp_code:
                return render(request, "user/profile/profile_edit.html", {
                    "show_otp_modal": True,
                    "otp_error": "Invalid OTP code. Please try again."
                })

            if otp_record.expires_at < timezone.now():
                return render(request, "user/profile/profile_edit.html", {
                    "show_otp_modal": True,
                    "otp_error": "The OTP code has expired. Please request a new code."
                })

            if request.user.socialaccount_set.exists() and pending_data["email"] != request.user.email.lower():
                messages.error(request, "Google authenticated users cannot change their email address.")
                return render(request, "user/profile/profile_edit.html")
>>>>>>> 8e77622 (Refactored the user input validation)

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

<<<<<<< HEAD
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

=======
            messages.success(request, "Profile updated successfully!")
            return redirect("profiles:profile")

        # 2. Standard Update or Email/Mobile change detection
        email = request.POST.get("email", "").strip().lower()
        mobile_number = request.POST.get("mobile_number", "").strip() or None

        email_changed = email and email != request.user.email.lower()
        mobile_changed = mobile_number != (request.user.mobile_number or None)

        if email_changed or mobile_changed:
            return profile_send_otp_view(request)

        fullname = request.POST.get("fullname", "").strip()
        if not fullname:
            messages.error(request, "Full name is required.")
            return render(request, "user/profile/profile_edit.html")

        has_changed = (
            fullname != request.user.fullname or
            request.FILES.get("profile_image") is not None
        )

        if has_changed:
>>>>>>> 8e77622 (Refactored the user input validation)
            request.user.fullname = fullname
            if request.FILES.get("profile_image"):
                request.user.profile_image = request.FILES["profile_image"]
            request.user.save()
<<<<<<< HEAD

            return JsonResponse({"status": "success"})
=======
            messages.success(request, "Profile updated successfully!")

        return redirect("profiles:profile")
>>>>>>> 8e77622 (Refactored the user input validation)

    return render(request, "user/profile/profile_edit.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def addresses_view(request):
    addresses = Address.objects.filter(user=request.user)
<<<<<<< HEAD
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
=======
    return render(request, "user/profile/addresses.html", {"addresses": addresses})
>>>>>>> 8e77622 (Refactored the user input validation)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def address_save_view(request):
    if request.method != "POST":
<<<<<<< HEAD
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
=======
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

    # 1. Required fields check
    if not full_name or not phone_number or not address_line_1 or not city or not state or not pincode:
        messages.error(request, "All required fields must be filled.")
        return redirect("addresses")

    # 2. Validation checks using reusable services helpers
    error = validate_full_name(full_name) or validate_phone_number(phone_number) or validate_pincode(pincode)
    if error:
        messages.error(request, error)
        return redirect("addresses")

    # 3. Save or Update Address
    badge_val = "DEFAULT" if is_default else (badge if badge != "DEFAULT" else "")
>>>>>>> 8e77622 (Refactored the user input validation)

    if address_id:
        try:
            addr = Address.objects.get(id=address_id, user=request.user)
<<<<<<< HEAD
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
=======
            has_changed = (
                addr.full_name != full_name or
                addr.phone_number != phone_number or
                addr.address_line_1 != address_line_1 or
                (addr.address_line_2 or "") != (address_line_2 or "") or
                addr.city != city or
                addr.state != state or
                addr.pincode != pincode or
                addr.is_default != is_default or
                addr.label != label
            )
            if has_changed:
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
>>>>>>> 8e77622 (Refactored the user input validation)
            user=request.user,
            full_name=full_name,
            phone_number=phone_number,
            address_line_1=address_line_1,
            address_line_2=address_line_2 or None,
            city=city,
            state=state,
            pincode=pincode,
            is_default=is_default,
<<<<<<< HEAD
            label=label,
            badge="DEFAULT" if is_default else badge
        )
        addr.save()
        return JsonResponse({"status": "success", "message": "Location record created successfully", "id": str(addr.id)}, status=201)
=======
            badge=badge_val,
            label=label
        )
        messages.success(request, "Address created successfully!")

    return redirect("addresses")
>>>>>>> 8e77622 (Refactored the user input validation)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def address_delete_view(request, address_id):
    if request.method != "POST":
<<<<<<< HEAD
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
=======
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
>>>>>>> 8e77622 (Refactored the user input validation)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_password_send_otp_view(request):
    if request.user.socialaccount_set.exists():
<<<<<<< HEAD
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
=======
        messages.error(request, "Social authenticated users cannot change their password.")
        return redirect("profiles:profile")

    if request.method != "POST":
        return redirect("profiles:profile_password")

    current_pwd = request.POST.get("current_pwd", "").strip()
    new_pwd     = request.POST.get("new_pwd", "").strip()
    confirm_pwd = request.POST.get("confirm_pwd", "").strip()

    # 1. Validate Password Inputs
    if not current_pwd or not request.user.check_password(current_pwd):
        messages.error(request, "Incorrect current password.")
        return render(request, "user/profile/password.html")

    if not new_pwd or new_pwd != confirm_pwd:
        messages.error(request, "New passwords do not match or are empty.")
        return render(request, "user/profile/password.html")

    strength_error = validate_password_strength(new_pwd)
    if strength_error:
        messages.error(request, strength_error)
        return render(request, "user/profile/password.html")

    # 2. Send OTP via services.py helper
    if not send_password_change_otp(request.user):
        messages.error(request, "Failed to send OTP email. Please try again.")
        return render(request, "user/profile/password.html")

    # 3. Show OTP Modal
    return render(request, "user/profile/password.html", {
        "show_otp_modal": True,
        "temp_current_pwd": current_pwd,
        "temp_new_pwd": new_pwd,
        "temp_confirm_pwd": confirm_pwd,
    })
>>>>>>> 8e77622 (Refactored the user input validation)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def profile_password_view(request):
<<<<<<< HEAD
    is_social = request.user.socialaccount_set.exists()
    if is_social:
        if request.method == "POST":
            return JsonResponse({"status": "error", "message": "Social authenticated users cannot change their password."}, status=400)
=======
    # 1. Social authenticated users cannot change password
    if request.user.socialaccount_set.exists():
        if request.method == "POST":
            messages.error(request, "Social authenticated users cannot change their password.")
>>>>>>> 8e77622 (Refactored the user input validation)
        return redirect('profiles:profile')

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        current_pwd = request.POST.get("current_pwd", "").strip()
<<<<<<< HEAD
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
=======
        new_pwd     = request.POST.get("new_pwd", "").strip()
        confirm_pwd = request.POST.get("confirm_pwd", "").strip()

        # 2. Verify OTP Record
        try:
            otp_record = OTPVerification.objects.filter(
                user=request.user, purpose="password_change", verified=False
            ).latest('created_at')
        except OTPVerification.DoesNotExist:
            messages.error(request, "OTP not found. Please request a new code.")
            return render(request, "user/profile/password.html")

        if entered_otp != otp_record.otp_code:
            return render(request, "user/profile/password.html", {
                "show_otp_modal": True,
                "otp_error": "Invalid OTP code. Please try again.",
                "temp_current_pwd": current_pwd,
                "temp_new_pwd": new_pwd,
                "temp_confirm_pwd": confirm_pwd,
            })

        if otp_record.expires_at < timezone.now():
            return render(request, "user/profile/password.html", {
                "show_otp_modal": True,
                "otp_error": "The OTP code has expired. Please request a new code.",
                "temp_current_pwd": current_pwd,
                "temp_new_pwd": new_pwd,
                "temp_confirm_pwd": confirm_pwd,
            })

        # 3. Validate Password Inputs
        if not current_pwd or not request.user.check_password(current_pwd):
            messages.error(request, "Incorrect current password.")
            return render(request, "user/profile/password.html")

        if not new_pwd or new_pwd != confirm_pwd:
            messages.error(request, "New passwords do not match or are empty.")
            return render(request, "user/profile/password.html")

        strength_error = validate_password_strength(new_pwd)
        if strength_error:
            messages.error(request, strength_error)
            return render(request, "user/profile/password.html")

        # 4. Save New Password & Keep User Logged In
        request.user.set_password(new_pwd)
        request.user.save()

        OTPVerification.objects.filter(user=request.user, purpose="password_change").delete()
        update_session_auth_hash(request, request.user)

        messages.success(request, "Password updated successfully!")
        return redirect("profiles:profile")
>>>>>>> 8e77622 (Refactored the user input validation)

    return render(request, "user/profile/password.html")
