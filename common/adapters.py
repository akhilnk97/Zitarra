from allauth.account.adapter import DefaultAccountAdapter


class NoMessageAccountAdapter(DefaultAccountAdapter):
    """
    This class silences the default flash messages that django-allauth
    (the Google login library) shows after login/logout.

    Without this, allauth would show messages like "Successfully signed in as..."
    which we don't want because we handle our own messages.
    """

    def add_message(self, request, level, message_template, message_context=None, extra_tags=''):
        if 'logged_in' in message_template:
            request.session['show_google_login_modal'] = True
