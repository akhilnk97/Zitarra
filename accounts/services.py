import random
<<<<<<< HEAD
=======
import re
>>>>>>> 8e77622 (Refactored the user input validation)
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import OTPVerification

<<<<<<< HEAD
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

=======
# ==========================================
# 1. FIELD VALIDATION HELPERS
# ==========================================

SPECIAL_CHARS = r"!@#$%^&*()_+-=[]{}|;':\",./<>?"


def validate_full_name(name):
    """Validates full name format."""
    if not name or len(name) < 3:
        return "Full name must be at least 3 characters."
    if name.startswith(" ") or name.endswith(" "):
        return "Please enter a valid full name (cannot start or end with spaces)."
    if "  " in name:
        return "Please enter a valid full name (no consecutive spaces allowed)."
    for char in name:
        if not char.isalpha() and not char.isspace():
            return "Please enter a valid full name (letters and single spaces only)."
    return None


def validate_phone_number(phone):
    """Validates 10-digit mobile number."""
    if not phone or len(phone) != 10 or not phone.isdigit():
        return "Phone number must be exactly 10 digits."
    return None


def validate_pincode(pincode):
    """Validates 6-digit postal pincode."""
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        return "Pincode must be exactly 6 digits."
    return None


def validate_password_strength(password):
    """Validates password security requirements."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if any(c.isspace() for c in password):
        return "Password must not contain spaces or whitespace."
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
>>>>>>> 8e77622 (Refactored the user input validation)
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter."
    if not any(c in SPECIAL_CHARS for c in password):
        return "Password must contain at least one special character."
<<<<<<< HEAD

    return None


=======
    return None


# ==========================================
# 2. EMAIL UTILITY HELPERS
# ==========================================

def send_mail_safe(subject, message, recipient, html_template=None, context=None):
    """Sends an email safely, logging to terminal in DEBUG mode if dispatch fails."""
    try:
        if html_template and context:
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            html_message = render_to_string(html_template, context)
            plain_message = strip_tags(html_message)
        else:
            html_message = None
            plain_message = message

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )
        return True

    except Exception:
        if settings.DEBUG:
            print(f"\n[DEBUG] SMTP Send Failed -> Subject: {subject} | Recipient: {recipient}")
            return True
        return False


# ==========================================
# 3. OTP GENERATION & EMAIL DISPATCH
# ==========================================

>>>>>>> 8e77622 (Refactored the user input validation)
def generate_otp():
    """Generates a random 6-digit numeric string."""
    return str(random.randint(100000, 999999))


def create_otp(user, purpose):
<<<<<<< HEAD
    """
    Generates a new OTP, persists it, and prints it for local development.
    Purposes include: "signup", "reset", "admin_reset", "profile_edit", "password_change"
    """
    OTPVerification.objects.filter(
        user=user,
        purpose=purpose,
        verified=False
    ).delete()
=======
    """Deletes previous unverified OTPs and generates a new 1-minute OTP."""
    OTPVerification.objects.filter(user=user, purpose=purpose, verified=False).delete()
>>>>>>> 8e77622 (Refactored the user input validation)

    otp_code = generate_otp()
    expiry_time = timezone.now() + timedelta(minutes=1)

    record = OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        email=user.email,
        purpose=purpose,
        expires_at=expiry_time,
    )

<<<<<<< HEAD
    print(f" OTP CODE: {otp_code} ")
    

=======
    print(f" >>> OTP CODE ({purpose}): {otp_code} <<< ")
>>>>>>> 8e77622 (Refactored the user input validation)
    return otp_code, record


def send_signup_otp(user, otp_code):
<<<<<<< HEAD
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
=======
    """Emails account activation OTP."""
    context = {
        "subject": "Zitarra Account Verification",
        "heading": "Verify Your Account",
        "user_name": user.fullname,
        "lead_text": "Thank you for registering with Zitarra! Use the verification code below to activate your account.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": False,
    }
    return send_mail_safe(context["subject"], None, user.email, "emails/otp_email.html", context)


def send_reset_otp(user, otp_code):
    """Emails password reset OTP."""
    context = {
        "subject": "Zitarra — Password Reset Code",
        "heading": "Reset Your Password",
        "user_name": user.fullname,
        "lead_text": "We received a request to reset your password. Use the verification code below to set up a new password.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": True,
    }
    return send_mail_safe(context["subject"], None, user.email, "emails/otp_email.html", context)


def send_password_change_otp(user):
    """Generates and emails password change verification OTP."""
    otp_code, _ = create_otp(user, "password_change")
    context = {
        "subject": "Zitarra — Password Change Verification Code",
        "heading": "Confirm Password Change",
        "user_name": user.fullname,
        "lead_text": "You are changing your account password. Use the verification code below to authorize the change.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": True,
    }
    return send_mail_safe(context["subject"], None, user.email, "emails/otp_email.html", context)


def send_profile_edit_otp(user, target_email):
    """Generates and emails profile update verification OTP to target_email."""
    otp_code, _ = create_otp(user, "profile_edit")
    context = {
        "subject": "Zitarra — Profile Update Verification Code",
        "heading": "Confirm Profile Update",
        "user_name": user.fullname,
        "lead_text": "You requested to update your profile email or phone. Use the code below to confirm changes.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": True,
    }
    return send_mail_safe(context["subject"], None, target_email, "emails/otp_email.html", context)


def send_admin_reset_otp(user):
    """Generates and emails admin password reset OTP."""
    otp_code, _ = create_otp(user, "admin_reset")
    context = {
        "subject": "Zitarra Admin — Password Reset Code",
        "heading": "Admin Password Reset",
        "user_name": user.fullname,
        "lead_text": "A request was received to reset your Zitarra administrator account password.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": True,
    }
    return send_mail_safe(context["subject"], None, user.email, "emails/otp_email.html", context)


# ==========================================
# 4. SESSION MANAGEMENT HELPERS
# ==========================================

def invalidate_user_sessions(user):
    """Invalidates all active database sessions belonging to the specified user."""
>>>>>>> 8e77622 (Refactored the user input validation)
    from django.contrib.sessions.models import Session
    from django.utils import timezone as tz

    active_sessions = Session.objects.filter(expire_date__gte=tz.now())
<<<<<<< HEAD

    for session in active_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.id):
=======
    for session in active_sessions:
        if session.get_decoded().get('_auth_user_id') == str(user.id):
>>>>>>> 8e77622 (Refactored the user input validation)
            session.delete()
