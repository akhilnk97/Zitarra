import time as time_module
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.utils import timezone

<<<<<<< HEAD
from .decorators import admin_required
from accounts.models import User, OTPVerification
from accounts.services import create_otp, send_mail_safe, validate_password_strength
=======
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models.functions import Lower

from .decorators import admin_required
from accounts.models import User, OTPVerification
from accounts.services import (
    create_otp,
    send_mail_safe,
    send_admin_reset_otp,
    validate_password_strength,
)
>>>>>>> 8e77622 (Refactored the user input validation)

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
<<<<<<< HEAD
            return render(request, "admin_panel/authentication/forgot_password.html", status=400)
=======
            return render(request, "admin_panel/authentication/forgot_password.html")
>>>>>>> 8e77622 (Refactored the user input validation)

        try:
            user = User.objects.get(email=email, is_staff=True)
        except User.DoesNotExist:
            messages.error(request, "This email address is not registered as an administrator.")
<<<<<<< HEAD
            return render(request, "admin_panel/authentication/forgot_password.html", status=400)

        otp_code, _ = create_otp(user, "admin_reset")
        sent = send_mail_safe(
            subject="Zitarra Admin — Password Reset Code",
            message=f"Hello {user.fullname},\n\nYour admin password reset OTP is:\n\n{otp_code}\n\nZitarra Team",
            recipient=email,
        )

        if not sent:
            messages.error(request, "Failed to send email. Please try again.")
            return render(request, "admin_panel/authentication/forgot_password.html", status=500)
=======
            return render(request, "admin_panel/authentication/forgot_password.html")

        if not send_admin_reset_otp(user):
            messages.error(request, "Failed to send email. Please try again.")
            return render(request, "admin_panel/authentication/forgot_password.html")
>>>>>>> 8e77622 (Refactored the user input validation)

        request.session["admin_reset_user_id"] = user.id
        return redirect("admin_forgot_password_otp")

    return render(request, "admin_panel/authentication/forgot_password.html")


def admin_forgot_password_otp_view(request):
    reset_user_id = request.session.get("admin_reset_user_id")
    if not reset_user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("admin_forgot_password")

    if request.method == "POST":
<<<<<<< HEAD
        entered_otp = request.POST.get("otp")
=======
        entered_otp = request.POST.get("otp", "").strip()
>>>>>>> 8e77622 (Refactored the user input validation)

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

<<<<<<< HEAD
        if entered_otp != otp_record.otp_code:
            messages.error(request, "Invalid OTP. Please try again.")
=======
        if not entered_otp or entered_otp != otp_record.otp_code:
            messages.error(request, "Invalid OTP code. Please try again.")
>>>>>>> 8e77622 (Refactored the user input validation)
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
<<<<<<< HEAD
        except User.DoesNotExist:
            return redirect("admin_forgot_password")

        otp_code, _ = create_otp(user, "admin_reset")
        send_mail_safe(
            subject="Zitarra Admin — New Reset Code",
            message=f"Hello {user.fullname},\n\nYour new OTP is:\n\n{otp_code}\n\nZitarra Team",
            recipient=user.email,
        )
        messages.success(request, "A new code has been sent.")

=======
            send_admin_reset_otp(user)
            messages.success(request, "A new code has been sent.")
        except User.DoesNotExist:
            return redirect("admin_forgot_password")

>>>>>>> 8e77622 (Refactored the user input validation)
    return redirect("admin_forgot_password_otp")


def admin_forgot_password_reset_view(request):
    reset_user_id = request.session.get("admin_reset_user_id")
    otp_verified  = request.session.get("admin_reset_otp_verified")

    if not reset_user_id or not otp_verified:
        messages.error(request, "Unauthorized. Please verify your OTP first.")
        return redirect("admin_forgot_password")

    if request.method == "POST":
<<<<<<< HEAD
        new_password     = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not new_password or not confirm_password:
            messages.error(request, "Both fields are required.")
            return render(request, "admin_panel/authentication/forgot_password_reset.html", status=400)
=======
        new_password     = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not new_password or new_password != confirm_password:
            messages.error(request, "Passwords do not match or are empty.")
            return render(request, "admin_panel/authentication/forgot_password_reset.html")
>>>>>>> 8e77622 (Refactored the user input validation)

        error = validate_password_strength(new_password)
        if error:
            messages.error(request, error)
<<<<<<< HEAD
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
=======
            return render(request, "admin_panel/authentication/forgot_password_reset.html")

        try:
            user = User.objects.get(id=reset_user_id)
            user.set_password(new_password)
            user.save()
        except User.DoesNotExist:
            return redirect("admin_forgot_password")

        request.session.pop("admin_reset_user_id", None)
        request.session.pop("admin_reset_otp_verified", None)
>>>>>>> 8e77622 (Refactored the user input validation)

        messages.success(request, "Password updated successfully. Please login.")
        return redirect("admin_login")

    return render(request, "admin_panel/authentication/forgot_password_reset.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_dashboard_view(request):
    context = {
        "total_users":     User.objects.filter(is_staff=False, is_verified=True).count(),
        "total_orders":    0,
        "total_products":  0,
        "total_sales":     0,
        "pending_returns": 0,
        "active_offers":   0,
        "admin_name":      request.user.fullname,
    }
    return render(request, "admin_panel/dashboard/dashboard.html", context)


def admin_logout_view(request):
    logout(request)
    return redirect("admin_login")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_users_view(request):
<<<<<<< HEAD
    from django.db.models import Q
    from django.core.paginator import Paginator
    from django.db.models.functions import Lower


    search_query = request.GET.get("search", "").strip()
    filter_val   = request.GET.get("filter", "All Users").strip()
    sort_val     = request.GET.get("sort", "Latest First").strip()
    per_page_str = request.GET.get("per_page", "10").strip()
    page_str     = request.GET.get("page", "1").strip()

    try:
        per_page = int(per_page_str)
        if per_page not in [10, 25, 50]:
            per_page = 10
    except ValueError:
        per_page = 10

    try:
        page = int(page_str)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    queryset = User.objects.filter(is_staff=False)

=======
    # 1. Read URL Parameters
    search_query = request.GET.get("search", "").strip()
    filter_val   = request.GET.get("filter", "All Users").strip()
    sort_val     = request.GET.get("sort", "Latest First").strip()
    
    try:
        per_page = int(request.GET.get("per_page", 10))
        if per_page not in [10, 25, 50]: per_page = 10
    except ValueError:
        per_page = 10

    page = request.GET.get("page", 1)

    # 2. Base Query (Exclude Admins)
    queryset = User.objects.filter(is_staff=False)

    # 3. Apply Search
>>>>>>> 8e77622 (Refactored the user input validation)
    if search_query:
        queryset = queryset.filter(
            Q(fullname__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(mobile_number__icontains=search_query)
        )

<<<<<<< HEAD
=======
    # 4. Apply Status Filter
>>>>>>> 8e77622 (Refactored the user input validation)
    if filter_val == "Active Accounts":
        queryset = queryset.filter(is_blocked=False)
    elif filter_val == "Blocked Accounts":
        queryset = queryset.filter(is_blocked=True)

<<<<<<< HEAD
=======
    # 5. Apply Sorting
>>>>>>> 8e77622 (Refactored the user input validation)
    if sort_val == "Oldest First":
        queryset = queryset.order_by("id")
    elif sort_val == "Name (A-Z)":
        queryset = queryset.order_by(Lower("fullname").asc())
    elif sort_val == "Name (Z-A)":
        queryset = queryset.order_by(Lower("fullname").desc())
    else:
        queryset = queryset.order_by("-id")

<<<<<<< HEAD
    paginator = Paginator(queryset, per_page)
    page_obj  = paginator.get_page(page)

    mapped_users = []
    start_index  = (page_obj.number - 1) * per_page

    for i, u in enumerate(page_obj.object_list):
        serial_number = start_index + i + 1

        mapped_users.append({
            "id":      u.id,
            "name":    u.fullname,
            "email":   u.email,
            "mobile":  u.mobile_number or "N/A",
            "avatar":  u.profile_image.url if u.profile_image else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80",
            "blocked": u.is_blocked,
            "s_no":    f"{serial_number:03d}",
        })

=======
    # 6. Pagination
    paginator = Paginator(queryset, per_page)
    page_obj  = paginator.get_page(page)

    # 7. Map Table Rows & Serial Numbers
    mapped_users = []
    start_index  = (page_obj.number - 1) * per_page

    for i, user in enumerate(page_obj.object_list):
        mapped_users.append({
            "id":      user.id,
            "name":    user.fullname,
            "email":   user.email,
            "mobile":  user.mobile_number or "N/A",
            "avatar":  user.profile_image.url if user.profile_image else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80",
            "blocked": user.is_blocked,
            "s_no":    start_index + i + 1,
        })

    # 8. Clean Context Dictionary
>>>>>>> 8e77622 (Refactored the user input validation)
    context = {
        "users":        mapped_users,
        "page_obj":     page_obj,
        "search_query": search_query,
        "filter_val":   filter_val,
        "sort_val":     sort_val,
        "per_page":     per_page,
        "admin_name":   request.user.fullname,
<<<<<<< HEAD
        "filter_all":     filter_val == "All Users",
        "filter_active":  filter_val == "Active Accounts",
        "filter_blocked": filter_val == "Blocked Accounts",
        "sort_latest":    sort_val == "Latest First",
        "sort_oldest":    sort_val == "Oldest First",
        "sort_name_az":   sort_val == "Name (A-Z)",
        "sort_name_za":   sort_val == "Name (Z-A)",
        "per_page_10":    per_page == 10,
        "per_page_25":    per_page == 25,
        "per_page_50":    per_page == 50,
=======
>>>>>>> 8e77622 (Refactored the user input validation)
    }
    return render(request, "admin_panel/users/users.html", context)


<<<<<<< HEAD
@admin_required
def admin_toggle_block_view(request, user_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
=======
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_toggle_block_view(request, user_id):
    if request.method != "POST":
        return redirect("admin_users")
>>>>>>> 8e77622 (Refactored the user input validation)

    try:
        user = User.objects.get(id=user_id, is_staff=False)
        user.is_blocked = not user.is_blocked
<<<<<<< HEAD
        user.is_active = not user.is_blocked
        user.save()

        return JsonResponse({
            "status": "success",
            "is_blocked": user.is_blocked,
        })

    except User.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "User not found",
        }, status=404)
=======
        user.is_active  = not user.is_blocked
        user.save()

        status_text = "blocked" if user.is_blocked else "unblocked"
        messages.success(request, f"User '{user.fullname}' has been {status_text}.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")

    return redirect("admin_users")
>>>>>>> 8e77622 (Refactored the user input validation)


from user_panel.views import custom_404_view

def admin_unimplemented_view(request):
    return custom_404_view(request)
<<<<<<< HEAD
=======

>>>>>>> 8e77622 (Refactored the user input validation)
