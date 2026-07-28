from django.shortcuts import render
from django.views.decorators.cache import cache_control
from admin_panel.decorators import admin_required
from accounts.models import User

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


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@admin_required
def admin_unimplemented_view(request):
    return render(request, "admin_panel/404.html", {"admin_name": request.user.fullname})
