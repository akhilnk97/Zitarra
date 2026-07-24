<<<<<<< HEAD
from django.shortcuts import render
=======
from django.shortcuts import render, redirect
>>>>>>> 8e77622 (Refactored the user input validation)
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from accounts.decorators import user_not_blocked


def landing_view(request):
<<<<<<< HEAD
=======
    if request.user.is_authenticated:
        return redirect("home")
>>>>>>> 8e77622 (Refactored the user input validation)
    return render(request, "user/panel/landing.html")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='/login/')
@user_not_blocked
def home_view(request):
    google_signup = request.session.pop("google_signup_success", False)
<<<<<<< HEAD
    return render(request, "user/panel/home.html", {
        "google_signup": google_signup,
    })
=======
    return render(request, "user/panel/home.html", {"google_signup": google_signup})
>>>>>>> 8e77622 (Refactored the user input validation)


def custom_404_view(request, exception=None):
    if request.path.startswith('/admin-panel/'):
<<<<<<< HEAD
        context = {}
        if request.user.is_authenticated and request.user.is_staff:
            context["admin_name"] = request.user.fullname
        return render(request, "admin_panel/404.html", context, status=404)
=======
        admin_name = request.user.fullname if (request.user.is_authenticated and request.user.is_staff) else None
        return render(request, "admin_panel/404.html", {"admin_name": admin_name}, status=404)
>>>>>>> 8e77622 (Refactored the user input validation)
    return render(request, "404.html", status=404)

