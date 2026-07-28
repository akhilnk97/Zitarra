from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control


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


def user_member_required(view_func):
    """
    Composite decorator that enforces:
    1. Cache control (no cache)
    2. Authentication (login required)
    3. Account verification (user not blocked)
    """
    decorator = cache_control(no_cache=True, no_store=True, must_revalidate=True)(
        login_required(login_url='/login/')(
            user_not_blocked(view_func)
        )
    )
    return decorator
