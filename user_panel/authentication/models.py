from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver


class UserManager(BaseUserManager):
    """
    Custom manager for User model where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model extending AbstractUser. Use email as unique login identifier.
    """
    username = None
    fullname      = models.CharField(max_length=255, blank=True, default="")
    email         = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    referral_code = models.CharField(max_length=50, blank=True, null=True)
    profile_image = models.ImageField(upload_to='users/', blank=True, null=True)
    role          = models.CharField(max_length=20, default='user')
    is_verified   = models.BooleanField(default=False)
    is_blocked    = models.BooleanField(default=False)
    updated_at    = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['fullname']

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class OTPVerification(models.Model):
    """
    Stores one-time passcode verification details.
    """
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code   = models.CharField(max_length=10)
    email      = models.EmailField()
    purpose    = models.CharField(max_length=50)
    expires_at = models.DateTimeField()
    verified   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


@receiver(pre_social_login)
def handle_google_login(sender, request, sociallogin, **kwargs):
    """
    Pre-login signal handler for allauth social logins.
    Prevents blocked users from logging in via Google, and sets default details for new users.
    """
    user  = sociallogin.user
    extra = sociallogin.account.extra_data

    # Check if this Google user has logged in before using Google auth
    from allauth.socialaccount.models import SocialAccount
    uid = sociallogin.account.uid
    provider = sociallogin.account.provider
    if provider == 'google':
        if SocialAccount.objects.filter(provider=provider, uid=uid).exists():
            request.session['google_login_type'] = 'welcome_back'
        else:
            request.session['google_login_type'] = 'welcome'

    email = None
    if hasattr(sociallogin, 'email_addresses'):
        for email_address in sociallogin.email_addresses:
            if email_address.email:
                email = email_address.email
                break
    if not email and user.email:
        email = user.email

    if email:
        try:
            db_user = User.objects.get(email__iexact=email.strip())
            if db_user.is_blocked:
                from django.contrib import messages
                from allauth.core.exceptions import ImmediateHttpResponse
                from django.shortcuts import redirect
                messages.error(request, "Your account has been blocked. Contact support.")
                raise ImmediateHttpResponse(redirect('login'))
        except User.DoesNotExist:
            pass

    if user.pk:
        try:
            db_user = User.objects.get(pk=user.pk)
            if db_user.is_blocked:
                from django.contrib import messages
                from allauth.core.exceptions import ImmediateHttpResponse
                from django.shortcuts import redirect
                messages.error(request, "Your account has been blocked. Contact support.")
                raise ImmediateHttpResponse(redirect('login'))
        except User.DoesNotExist:
            pass

    if not user.pk:
        if not user.fullname:
            user.fullname = extra.get('name', '') or extra.get('given_name', 'Google User')
        user.is_verified = True