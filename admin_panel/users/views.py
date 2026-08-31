from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models.functions import Lower

from common.decorators import admin_required
from user_panel.authentication.models import User

@admin_required
def admin_users_view(request):
    search_query = request.GET.get("search", "").strip()
    filter_val   = request.GET.get("filter", "All Users").strip()
    sort_val     = request.GET.get("sort", "Latest First").strip()
    page_str     = request.GET.get("page", "1").strip()

    try:
        page = int(page_str)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    queryset = User.objects.filter(is_staff=False)

    if search_query:
        queryset = queryset.filter(
            Q(fullname__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(mobile_number__icontains=search_query)
        )

    if filter_val == "Active Accounts":
        queryset = queryset.filter(is_blocked=False)
    elif filter_val == "Blocked Accounts":
        queryset = queryset.filter(is_blocked=True)

    sort_upper = sort_val.upper()
    if sort_upper in ["OLDEST FIRST", "OLDEST"]:
        sort_val = "Oldest First"
        queryset = queryset.order_by("id")
    elif sort_upper in ["NAME (A-Z)", "NAME A-Z", "A-Z"]:
        sort_val = "Name (A-Z)"
        queryset = queryset.order_by(Lower("fullname").asc())
    elif sort_upper in ["NAME (Z-A)", "NAME Z-A", "Z-A"]:
        sort_val = "Name (Z-A)"
        queryset = queryset.order_by(Lower("fullname").desc())
    else:
        sort_val = "Latest First"
        queryset = queryset.order_by("-id")

    per_page = 10
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
            "s_no":    serial_number,
        })

    context = {
        "users":        mapped_users,
        "page_obj":     page_obj,
        "search_query": search_query,
        "filter_val":   filter_val,
        "sort_val":     sort_val,
        "admin_name":   request.user.fullname,
        "filter_all":     filter_val == "All Users",
        "filter_active":  filter_val == "Active Accounts",
        "filter_blocked": filter_val == "Blocked Accounts",
        "sort_latest":    sort_val == "Latest First",
        "sort_oldest":    sort_val == "Oldest First",
        "sort_name_az":   sort_val == "Name (A-Z)",
        "sort_name_za":   sort_val == "Name (Z-A)",
    }
    return render(request, "admin_panel/users/users.html", context)


@admin_required
def admin_toggle_block_view(request, user_id):
    if request.method != "POST":
        messages.error(request, "Method not allowed")
        return redirect("admin_users")

    try:
        user = User.objects.get(id=user_id, is_staff=False)
        user.is_blocked = not user.is_blocked
        user.is_active = not user.is_blocked
        user.save()

        if user.is_blocked:
            messages.success(request, f"User {user.fullname} has been blocked successfully.")
        else:
            messages.success(request, f"User {user.fullname} has been unblocked successfully.")

    except User.DoesNotExist:
        messages.error(request, "User not found")

    return redirect("admin_users")
