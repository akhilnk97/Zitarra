from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from functools import wraps


def user_not_blocked(view_func):
    """
    Decorator to check if the authenticated user has been blocked.
    If blocked, logs them out and redirects to the login page.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_blocked:
            logout(request)
            messages.error(request, "Your account has been blocked. Contact support.")
            return redirect("login")

        return view_func(request, *args, **kwargs)

    return wrapper
