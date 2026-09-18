from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth import get_user_model
from common.decorators import user_member_required
from common.services import calculate_order_totals, is_ajax, get_or_create_user_referral_code
from user_panel.cart.models import Cart
from user_panel.orders.models import Order
from user_panel.coupons.models import Coupon
from user_panel.profiles.models import Referral
from user_panel.wallet.models import Wallet

User = get_user_model()


@user_member_required
def apply_coupon_view(request):
    if request.method != 'POST':
        return redirect('checkout')
    def return_response(status, msg, **extra):
        if is_ajax(request):
            data = {'status': status, 'message': msg}
            data.update(extra)
            return JsonResponse(data)
        if status == 'warning':
            messages.warning(request, msg)
        elif status == 'error':
            messages.error(request, msg)
        else:
            messages.success(request, msg)
        referer = request.META.get('HTTP_REFERER', '')
        if 'cart' in referer:
            return redirect('cart_view')
        return redirect('checkout')

    payment_method = request.POST.get('payment_method')
    if payment_method == 'CASH_ON_DELIVERY':
        return return_response('warning', 'Coupons are only supported for Razorpay (Online Payment). Cash on Delivery (COD) is not eligible for coupon discounts.')

    code = request.POST.get('coupon_code', '').strip().upper()
    if not code:
        return return_response('error', 'Please enter a promo code.')

    existing_coupon = request.session.get('applied_coupon')
    if existing_coupon:
        if existing_coupon.upper() == code:
            return return_response('warning', f"Coupon '{code}' is already applied to your order.")
        else:
            return return_response('warning', f"A coupon ('{existing_coupon}') is already applied. Please remove it before applying a new coupon.")

    try:
        cart = request.user.cart
        subtotal = cart.get_subtotal()
        cart_items = list(cart.items.all())
    except Cart.DoesNotExist:
        return return_response('error', 'Your cart is empty.')

    coupon = Coupon.objects.filter(code__iexact=code, is_active=True).first()
    if not coupon:
        return return_response('error', f"Invalid or expired promo code '{code}'.")

    # First-order only eligibility check
    if coupon.is_first_order_only:
        user_orders_count = Order.objects.filter(user=request.user).exclude(order_status='CANCELLED').count()
        if user_orders_count > 0:
            return return_response('error', f"Coupon '{coupon.code}' is strictly reserved for first-time customers on their first purchase.")

    # Per-user usage limit check
    if coupon.usage_limit_per_user:
        user_redemptions = Order.objects.filter(user=request.user, coupon_code__iexact=coupon.code).exclude(order_status='CANCELLED').count()
        if user_redemptions >= coupon.usage_limit_per_user:
            return return_response('error', f"You have already redeemed coupon '{coupon.code}'.")

    discount_amount = coupon.calculate_discount(subtotal, cart_items=cart_items)

    if discount_amount <= Decimal('0.00'):
        if coupon.offer_type == 'CATEGORY_SPECIFIC':
            return return_response('error', f"Coupon '{coupon.code}' is only valid for items in eligible categories.")
        elif coupon.offer_type == 'PRODUCT_SPECIFIC':
            return return_response('error', f"Coupon '{coupon.code}' is only valid for eligible products in your cart.")
        elif subtotal < coupon.min_purchase:
            return return_response('error', f"Coupon '{coupon.code}' requires a minimum subtotal of ₹{coupon.min_purchase:,.2f}.")
        else:
            return return_response('error', f"Coupon '{coupon.code}' cannot be applied to this order.")

    request.session['applied_coupon'] = coupon.code
    shipping_cost, tax_amount, total_price = calculate_order_totals(subtotal, discount_amount)
    msg = f"Coupon '{coupon.code}' applied! You saved ₹{discount_amount:,.2f}."

    return return_response('success', msg,
        coupon_code=coupon.code,
        discount_amount=f"{discount_amount:,.2f}",
        subtotal=f"{subtotal:,.2f}",
        shipping_cost=f"{shipping_cost:,.2f}",
        tax_amount=f"{tax_amount:,.2f}",
        total_price=f"{total_price:,.2f}"
    )


@user_member_required
def remove_coupon_view(request):
    if 'applied_coupon' in request.session:
        removed_code = request.session.pop('applied_coupon')
        msg = f"Coupon '{removed_code}' removed."
    else:
        msg = "No coupon was applied."

    try:
        cart = request.user.cart
        subtotal = cart.get_subtotal()
    except Cart.DoesNotExist:
        subtotal = Decimal('0.00')

    shipping_cost, tax_amount, total_price = calculate_order_totals(subtotal, Decimal('0.00'))

    if is_ajax(request):
        return JsonResponse({
            'status': 'success',
            'message': msg,
            'subtotal': f"{subtotal:,.2f}",
            'shipping_cost': f"{shipping_cost:,.2f}",
            'tax_amount': f"{tax_amount:,.2f}",
            'total_price': f"{total_price:,.2f}",
        })

    messages.success(request, msg)
    referer = request.META.get('HTTP_REFERER', '')
    if 'cart' in referer:
        return redirect('cart_view')
    return redirect('checkout')


def referral_landing_view(request):
    """
    Handles Referral Link landing via Token URL or Referral Code:
    e.g. /referral/?token=XYZ or /referral/?ref=ZTR-REF-8A3X
    """
    token = request.GET.get('token', '').strip()
    ref_code = request.GET.get('ref', '').strip()

    referrer = None
    if token:
        referral_rec = Referral.objects.filter(token=token).first()
        if referral_rec:
            referrer = referral_rec.referrer
            ref_code = referral_rec.referral_code
    elif ref_code:
        referrer = User.objects.filter(referral_code__iexact=ref_code).first()

    if referrer:
        request.session['referral_code'] = ref_code
        messages.success(
            request,
            f"Welcome to Zitarra! You were referred by {referrer.fullname or referrer.email}. Sign up today to receive your ₹100 welcome bonus!"
        )
    else:
        messages.warning(request, "Invalid or expired referral link.")

    return redirect('signup')


@user_member_required
def user_referrals_view(request):
    user = request.user
    ref_code = get_or_create_user_referral_code(user)

    scheme = 'https' if request.is_secure() else 'http'
    domain = request.get_host()
    referral_link = f"{scheme}://{domain}/referral/?ref={ref_code}"

    referrals = Referral.objects.filter(referrer=user).select_related('referred_user').order_by('-created_at')

    total_invites = referrals.count()
    registered_count = referrals.filter(status__in=['REGISTERED', 'COMPLETED']).count()
    completed_count = referrals.filter(status='COMPLETED').count()

    wallet, _ = Wallet.objects.get_or_create(user=user)
    total_earned = wallet.transactions.filter(
        transaction_type='CREDIT',
        purpose='REFERRAL_BONUS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    context = {
        'referral_code': ref_code,
        'referral_link': referral_link,
        'referrals': referrals,
        'total_invites': total_invites,
        'registered_count': registered_count,
        'completed_count': completed_count,
        'total_earned': total_earned,
        'active_tab': 'referrals',
    }
    return render(request, 'user/referrals/referrals.html', context)
