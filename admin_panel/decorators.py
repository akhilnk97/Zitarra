from django.shortcuts import redirect
from functools import wraps


def admin_required(view_func):
    """
    A decorator that protects admin-only pages.

    If the user is not logged in → redirect to the admin login page.
    If the user is logged in but is not a staff member → redirect to home page.
    If the user is logged in and is a staff member → let them through.

    Usage: Put @admin_required above any view function that only admins can access.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # If user is not logged in at all
        if not request.user.is_authenticated:
            return redirect("admin_login")

        # If user is logged in but is not an admin (is_staff = False)
        if not request.user.is_staff:
            return redirect("home")

        # User is a valid admin — run the actual view
        return view_func(request, *args, **kwargs)

    return wrapper
