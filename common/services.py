import random
import re
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from user_panel.authentication.models import OTPVerification
import base64
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import random
import string
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone as tz
from user_panel.orders.models import Coupon, Order
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal


def validate_full_name(name):
    """
    Validates a recipient full name.
    Must contain only letters and single spaces between words, min 3, max 60 chars.
    Cannot have leading/trailing spaces or consecutive spaces.
    """
    if not name or len(name.strip()) < 3:
        return "Full name must be at least 3 characters."
    if name.startswith(" ") or name.endswith(" "):
        return "Full name cannot start or end with a space."
    if "  " in name:
        return "Full name cannot contain consecutive spaces."
    if len(name) > 60:
        return "Full name cannot exceed 60 characters."
    if not re.match(r"^[A-Za-z]+( [A-Za-z]+)*$", name):
        return "Full name can only contain letters and single spaces between words."
    return None


def validate_phone_number(phone):
    """
    Validates a 10-digit mobile number starting with 6-9.
    """
    if not phone or len(phone.strip()) == 0:
        return "Phone number is required."
    if " " in phone:
        return "Phone number cannot contain spaces."
    if not re.match(r"^[6-9]\d{9}$", phone):
        return "Phone number must be a valid 10-digit number starting with 6, 7, 8, or 9."
    return None


def validate_pincode(pincode):
    """
    Validates a 6-digit postal pincode (cannot start with 0).
    """
    if not pincode or len(pincode.strip()) == 0:
        return "Pincode is required."
    if " " in pincode:
        return "Pincode cannot contain spaces."
    if not re.match(r"^[1-9]\d{5}$", pincode):
        return "Pincode must be exactly 6 digits and cannot start with 0."
    return None


def validate_city(city):
    """
    Validates city name.
    """
    if not city or len(city.strip()) < 2:
        return "City must be at least 2 characters."
    if city.startswith(" ") or city.endswith(" "):
        return "City cannot start or end with a space."
    if "  " in city:
        return "City cannot contain consecutive spaces."
    if len(city) > 60:
        return "City cannot exceed 60 characters."
    if not re.match(r"^[A-Za-z]+([ \-][A-Za-z]+)*$", city):
        return "City can only contain letters, hyphens, and single spaces."
    return None


def validate_state(state):
    """
    Validates state name.
    """
    if not state or len(state.strip()) < 2:
        return "State must be at least 2 characters."
    if state.startswith(" ") or state.endswith(" "):
        return "State cannot start or end with a space."
    if "  " in state:
        return "State cannot contain consecutive spaces."
    if len(state) > 60:
        return "State cannot exceed 60 characters."
    if not re.match(r"^[A-Za-z]+([ \-][A-Za-z]+)*$", state):
        return "State can only contain letters, hyphens, and single spaces."
    return None


def validate_address_line(line, field_name="Address line"):
    """
    Validates an address line (e.g. street, building, apartment).
    Must be at least 3 characters, cannot have consecutive spaces,
    must contain alphanumeric characters and only standard address punctuation.
    """
    if not line or len(line.strip()) < 3:
        return f"{field_name} must be at least 3 characters."
    if line.startswith(" ") or line.endswith(" "):
        return f"{field_name} cannot start or end with a space."
    if "  " in line:
        return f"{field_name} cannot contain consecutive spaces."
    if len(line) > 255:
        return f"{field_name} cannot exceed 255 characters."
    # Must have at least 2 alphanumeric characters so things like &&& or --- are rejected
    alnum_count = sum(1 for c in line if c.isalnum())
    if alnum_count < 2:
        return f"{field_name} must contain meaningful address details, not only symbols."
    # Disallow invalid symbols like &, $, %, *, ^, @, !, ~, `, etc.
    if not re.match(r"^[A-Za-z0-9\s,\-/#\.:;']+$", line):
        return f"{field_name} contains invalid special characters (only standard address punctuation like , - / # . allowed)."
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
            print(f"SMTP SEND FAILED (DEBUG MODE). REASON: {e}")
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
    

    active_sessions = Session.objects.filter(expire_date__gte=tz.now())

    for session in active_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.id):
            session.delete()


ALLOWED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.avif')


def is_valid_image_file(file_obj):
    """
    Checks uploaded image files.
    Returns True if file exists and has a valid image extension.
    """
    if file_obj and hasattr(file_obj, 'name'):
        return file_obj.name.lower().endswith(ALLOWED_IMAGE_EXTENSIONS)
    return False


def save_base64_image(base64_string, filename):
    """
    Converts a base64 image string (from Cropper.js) into a Django ContentFile object.
    Returns None if base64_string is empty or invalid.
    """
    if base64_string and base64_string.startswith("data:image"):
        try:
            format_part, data_part = base64_string.split(";base64,")
            extension = format_part.split('/')[-1].lower()
            decoded_bytes = base64.b64decode(data_part)
            return ContentFile(decoded_bytes, name=f"{filename}.{extension}")
        except Exception:
            return None
    return None


from decimal import Decimal

def calculate_order_totals(subtotal, discount_amount=Decimal('0.00')):
    """
    Calculates dynamic shipping cost, 5% GST tax, and total price with optional coupon discount.
    Rules:
    - Shipping: FREE (0.00) if subtotal >= 5000.00, else 150.00.
    - Tax: 5% GST on discounted subtotal.
    - Total: (subtotal - discount_amount) + shipping_cost + tax_amount
    """
    subtotal = Decimal(str(subtotal))
    discount_amount = Decimal(str(discount_amount or 0))

    if subtotal == Decimal('0.00'):
        return Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

    discounted_subtotal = max(Decimal('0.00'), subtotal - discount_amount)

    if subtotal >= Decimal('5000.00'):
        shipping_cost = Decimal('0.00')
    else:
        shipping_cost = Decimal('150.00')

    tax_amount = (discounted_subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
    total_price = discounted_subtotal + shipping_cost + tax_amount
    return shipping_cost, tax_amount, total_price


def is_ajax(request):
    """
    Helper function to check if the incoming request is an asynchronous AJAX request.
    """
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or
        request.POST.get('is_ajax') == 'true' or
        request.GET.get('is_ajax') == 'true'
    )


def get_eligible_coupons(user=None, subtotal=None, limit=None):
    """
    Returns active, valid coupons filtered specifically for the given user and subtotal context.
    
    Filters applied:
    1. Active status & date validity (valid_from <= now <= valid_to)
    2. Global usage limit (used_count < usage_limit)
    3. User first-order restriction: Hides 'is_first_order_only' coupons if user has 1+ non-cancelled orders
    4. Per-user usage limit: Hides coupons already redeemed by user up to 'usage_limit_per_user'
    5. Subtotal threshold (if subtotal is provided): Filters coupons where subtotal >= min_purchase
    6. Sorted by highest discount_value first. Optionally truncated to `limit` items.
    """

    now = timezone.now()
    qs = Coupon.objects.filter(is_active=True).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now)
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=now)
    )

    # Exclude global usage limit exceeded
    coupons_list = [c for c in qs if not (c.usage_limit and c.used_count >= c.usage_limit)]

    # Check user context if user is authenticated
    if user and user.is_authenticated:
        has_prior_orders = Order.objects.filter(user=user).exclude(order_status='CANCELLED').exists()
        
        filtered = []
        for c in coupons_list:
            # 1. First order restriction
            if c.is_first_order_only and has_prior_orders:
                continue
            
            # 2. Per-user usage limit restriction
            if c.usage_limit_per_user:
                user_uses = Order.objects.filter(user=user, coupon_code__iexact=c.code).exclude(order_status='CANCELLED').count()
                if user_uses >= c.usage_limit_per_user:
                    continue
            
            filtered.append(c)
        coupons_list = filtered

    # Subtotal threshold filter
    if subtotal is not None:
        subtotal_dec = Decimal(str(subtotal))
        coupons_list = [c for c in coupons_list if subtotal_dec >= c.min_purchase]

    # Sort by highest discount value first
    coupons_list.sort(key=lambda c: (c.discount_type == 'PERCENTAGE', c.discount_value), reverse=True)

    if limit and isinstance(limit, int):
        return coupons_list[:limit]
    return coupons_list


def get_or_create_user_referral_code(user):
    """
    Ensures user has a unique referral code like ZTR-REF-8A3X.
    """
    if not user or not user.is_authenticated:
        return ''

    if getattr(user, 'referral_code', None) and user.referral_code.strip():
        return user.referral_code

    
    UserModel = get_user_model()

    while True:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        code = f"ZTR-REF-{suffix}"
        if not UserModel.objects.filter(referral_code=code).exists():
            user.referral_code = code
            user.save(update_fields=['referral_code'])
            return code
