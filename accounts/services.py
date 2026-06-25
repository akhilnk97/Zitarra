import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import OTPVerification

def send_mail_safe(subject, message, recipient):
    """
    Sends an email. Returns True if successful, False otherwise.
    In local development (DEBUG=True), logs the email details to the console instead of dispatching.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return True

    except Exception as e:
        if settings.DEBUG:
            print("\n" + "="*80)
            print(f"SUBJECT: {subject}")
            print(f"RECIPIENT: {recipient}")
            print(f"MESSAGE:\n{message}")
            print("="*80 + "\n")
            return True
        return False


SPECIAL_CHARS = r"!@#$%^&*()_+-=[]{}|;':\",./<>?"

def validate_password_strength(password):
    """
    Validates a password strength.
    Returns validation error message string if invalid, None if valid.
    """
    if len(password) < 8:
        return "Password must be at least 8 characters."

    if any(c.isspace() for c in password):
        return "Password must not contain spaces or whitespace."

    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."

    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter."
    if not any(c in SPECIAL_CHARS for c in password):
        return "Password must contain at least one special character."

    return None


def generate_otp():
    """Generates a random 6-digit numeric string."""
    return str(random.randint(100000, 999999))


def create_otp(user, purpose):
    """
    Generates a new OTP, persists it, and prints it for local development.
    Purposes include: "signup", "reset", "admin_reset", "profile_edit", "password_change"
    """
    OTPVerification.objects.filter(
        user=user,
        purpose=purpose,
        verified=False
    ).delete()

    otp_code = generate_otp()
    expiry_time = timezone.now() + timedelta(minutes=1)

    record = OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        email=user.email,
        purpose=purpose,
        expires_at=expiry_time,
    )

    print(f" OTP CODE: {otp_code} ")
    

    return otp_code, record


def send_signup_otp(user, otp_code):
    subject = "Zitarra Account Verification"
    message = f"""Hello {user.fullname},

Your verification OTP is:

{otp_code}

Thank You,
Zitarra Team"""
    return send_mail_safe(subject, message, user.email)


def send_reset_otp(user, otp_code):
    subject = "Zitarra — Password Reset Code"
    message = f"""Hello {user.fullname},

Your password reset OTP is:

{otp_code}

If you did not request this, ignore this email.

Thank You,
Zitarra Team"""
    return send_mail_safe(subject, message, user.email)


def invalidate_user_sessions(user):
    """
    Invalidates all active database sessions belonging to the user.
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone as tz

    active_sessions = Session.objects.filter(expire_date__gte=tz.now())

    for session in active_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.id):
            session.delete()
