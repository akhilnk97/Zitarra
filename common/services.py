import random
import re
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from user_panel.authentication.models import OTPVerification
import base64
from django.core.files.base import ContentFile


def validate_full_name(name):
    """
    Validates a recipient full name.
    Returns error message string if invalid, None if valid.
    """
    if not name or len(name) < 3:
        return "Full name must be at least 3 characters."
    if name.startswith(" ") or name.endswith(" "):
        return "Please enter a valid full name (letters and single spaces only)."
    if "  " in name:
        return "Please enter a valid full name (letters and single spaces only)."
    for char in name:
        if not char.isalpha() and not char.isspace():
            return "Please enter a valid full name (letters and single spaces only)."
    return None


def validate_phone_number(phone):
    """
    Validates a 10-digit mobile number.
    Returns error message string if invalid, None if valid.
    """
    if not phone or len(phone) != 10 or not phone.isdigit():
        return "Phone number must be exactly 10 digits."
    return None


def validate_pincode(pincode):
    """
    Validates a 6-digit postal pincode.
    Returns error message string if invalid, None if valid.
    """
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        return "Pincode must be exactly 6 digits."
    return None


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

    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."

    if not any(c in SPECIAL_CHARS for c in password):
        return "Password must contain at least one special character."

    return None


def send_mail_safe(subject, message, recipient, html_template=None, context=None):
    """
    Sends an email. Returns True if successful, False otherwise.
    Supports both plain-text messages and HTML template rendering.
    In local development (DEBUG=True), logs the email details to the console instead of dispatching if it fails.
    """
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

    except Exception as e:
        if settings.DEBUG:
            print("\n" + "="*80)
            print(f"SMTP SEND FAILED (DEBUG MODE). EMAIL DETAILS:")
            print(f"SUBJECT: {subject}")
            print(f"RECIPIENT: {recipient}")
            if html_template and context:
                print(f"HTML TEMPLATE: {html_template}")
                print(f"CONTEXT: {context}")
            else:
                print(f"MESSAGE:\n{message}")
            print("="*80 + "\n")
            return True
        return False


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
    context = {
        "subject": subject,
        "heading": "Verify Your Account",
        "user_name": user.fullname,
        "lead_text": "Thank you for registering with Zitarra! Please use the verification code below to activate your account.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": False,
    }
    return send_mail_safe(subject, None, user.email, html_template="emails/otp_email.html", context=context)


def send_reset_otp(user, otp_code):
    subject = "Zitarra — Password Reset Code"
    context = {
        "subject": subject,
        "heading": "Reset Your Password",
        "user_name": user.fullname,
        "lead_text": "We received a request to reset your password. Use the verification code below to set up a new password.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": True,
    }
    return send_mail_safe(subject, None, user.email, html_template="emails/otp_email.html", context=context)


def send_password_change_otp(user):
    """
    Generates an OTP for password change and emails it to the user.
    Returns True if successfully sent, False otherwise.
    """
    otp_code, _ = create_otp(user, "password_change")
    subject = "Zitarra — Password Change Verification Code"
    context = {
        "subject": subject,
        "heading": "Confirm Password Change",
        "user_name": user.fullname,
        "lead_text": "You are changing your account password. Please use the verification code below to authorize the change.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": True,
    }
    return send_mail_safe(subject, None, user.email, html_template="emails/otp_email.html", context=context)


def send_profile_edit_otp(user, target_email):
    """
    Generates an OTP for profile email/mobile edit and emails it to target_email.
    Returns True if successfully sent, False otherwise.
    """
    otp_code, _ = create_otp(user, "profile_edit")
    subject = "Zitarra — Profile Update Verification Code"
    context = {
        "subject": subject,
        "heading": "Confirm Profile Update",
        "user_name": user.fullname,
        "lead_text": "You requested to update your email or mobile number. Please use the following code to confirm the changes.",
        "otp_code": otp_code,
        "expiry_time": "1 minute",
        "security_warning": True,
    }
    return send_mail_safe(subject, None, target_email, html_template="emails/otp_email.html", context=context)


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


def save_base64_image(base64_string, filename):
    """
    Converts a base64 image string (e.g. from Cropper.js) into a Django ContentFile object.
    Returns None if the base64_str is empty or invalid.
    """
    if base64_string and base64_string.startswith("data:image"):
        format_part, data_part = base64_string.split(";base64,")
        extension = format_part.split('/')[-1]
        decoded_bytes = base64.b64decode(data_part)
        return ContentFile(decoded_bytes, name=f"{filename}.{extension}")
    return None
    
