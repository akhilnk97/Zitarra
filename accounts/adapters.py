from allauth.account.adapter import DefaultAccountAdapter


class NoMessageAccountAdapter(DefaultAccountAdapter):
    """
    This class silences the default flash messages that django-allauth
    (the Google login library) shows after login/logout.

    Without this, allauth would show messages like "Successfully signed in as..."
    which we don't want because we handle our own messages.

    How it works:
      - DefaultAccountAdapter has a method called add_message() that adds flash messages.
      - We override it here with an empty method (just "pass") so it does nothing.
      - Django settings (in config/settings.py) points to this class via ACCOUNT_ADAPTER.
    """

    def add_message(self, request, level, message_template, message_context=None, extra_tags=''):
        pass
