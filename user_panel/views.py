from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from accounts.decorators import user_not_blocked


def landing_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "user/panel/landing.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def home_view(request):
    google_signup = request.session.pop("google_signup_success", False)
    return render(request, "user/panel/home.html", {"google_signup": google_signup})


def custom_404_view(request, exception=None):
    if request.path.startswith('/admin-panel/'):
        admin_name = request.user.fullname if (request.user.is_authenticated and request.user.is_staff) else None
        return render(request, "admin_panel/404.html", {"admin_name": admin_name}, status=404)
    return render(request, "404.html", status=404)

