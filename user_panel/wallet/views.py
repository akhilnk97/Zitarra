import json
import logging
from decimal import Decimal
import razorpay
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from common.decorators import user_member_required
from .models import Wallet, WalletTransaction
from django.db.models import Sum


logger = logging.getLogger(__name__)


@user_member_required
def wallet_view(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    filter_type = request.GET.get('type', '').strip().upper()
    search_q = request.GET.get('search', '').strip()
    page_num = request.GET.get('page', '1').strip()

    transactions = wallet.transactions.all()

    if filter_type in ['CREDIT', 'DEBIT']:
        transactions = transactions.filter(transaction_type=filter_type)

    if search_q:
        transactions = transactions.filter(
            description__icontains=search_q
        )

    total_refunded = wallet.transactions.filter(
        transaction_type='CREDIT',
        purpose__in=['ORDER_CANCELLATION_REFUND', 'ORDER_RETURN_REFUND']
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    total_added = wallet.transactions.filter(
        transaction_type='CREDIT',
        purpose='ADD_FUNDS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    total_debited = wallet.transactions.filter(
        transaction_type='DEBIT'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(page_num)

    context = {
        'wallet': wallet,
        'transactions': page_obj.object_list,
        'page_obj': page_obj,
        'filter_type': filter_type,
        'search_q': search_q,
        'total_refunded': total_refunded,
        'total_added': total_added,
        'total_debited': total_debited,
        'active_tab': 'wallet',
        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', ''),
    }
    return render(request, 'user/wallet/wallet.html', context)


@user_member_required
def create_wallet_razorpay_order_view(request):
    """
    Creates a Razorpay Order specifically for Wallet Top-Up.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    amount_str = request.POST.get('amount')
    if not amount_str and request.content_type == 'application/json':
        try:
            body_data = json.loads(request.body)
            amount_str = body_data.get('amount')
        except Exception:
            pass

    if not amount_str:
        return JsonResponse({'status': 'error', 'message': 'Amount is required.'}, status=400)

    try:
        amount = Decimal(str(amount_str))
        if amount < Decimal('10.00'):
            return JsonResponse({'status': 'error', 'message': 'Minimum top-up amount is ₹10.00.'}, status=400)
        if amount > Decimal('50000.00'):
            return JsonResponse({'status': 'error', 'message': 'Maximum single top-up limit is ₹50,000.00.'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid amount specified.'}, status=400)

    amount_in_paise = int(amount * 100)

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return JsonResponse({'status': 'error', 'message': 'Razorpay gateway is not configured.'}, status=500)

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {
                'user_id': request.user.id,
                'purpose': 'WALLET_TOPUP',
                'amount': str(amount)
            }
        }
        razorpay_order = client.order.create(data=razorpay_order_data)
        request.session['wallet_razorpay_order_id'] = razorpay_order['id']
        request.session['wallet_topup_amount'] = str(amount)
        logger.info(f"[RAZORPAY WALLET] Initiated top-up order {razorpay_order['id']} of ₹{amount:.2f} for user #{request.user.id} ({request.user.email})")
    except Exception as e:
        logger.error(f"[RAZORPAY WALLET] Order creation failed: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f"Razorpay initiation failed: {str(e)}"}, status=500)

    return JsonResponse({
        'status': 'success',
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order['id'],
        'amount': amount_in_paise,
        'amount_formatted': f"{amount:.2f}",
        'currency': 'INR',
        'user_name': request.user.get_full_name() or request.user.email,
        'user_email': request.user.email,
    })


@user_member_required
def verify_wallet_razorpay_payment_view(request):
    """
    Verifies Razorpay payment signature and credits top-up funds to user's Wallet.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_signature = request.POST.get('razorpay_signature')
    amount_str = request.POST.get('amount') or request.session.get('wallet_topup_amount')

    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        if request.content_type == 'application/json':
            try:
                body_data = json.loads(request.body)
                razorpay_payment_id = body_data.get('razorpay_payment_id')
                razorpay_order_id = body_data.get('razorpay_order_id')
                razorpay_signature = body_data.get('razorpay_signature')
                amount_str = body_data.get('amount') or amount_str
            except Exception as e:
                logger.error(f"[RAZORPAY WALLET] JSON parse error: {str(e)}")

    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        return JsonResponse({'status': 'error', 'message': 'Missing payment verification details.'}, status=400)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature,
    }

    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"[RAZORPAY WALLET] Verification failed: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Invalid payment signature.'}, status=400)
    except Exception as e:
        logger.error(f"[RAZORPAY WALLET] Verification error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Verification error: {str(e)}'}, status=400)

    # Convert amount
    try:
        amount = Decimal(str(amount_str))
    except (ValueError, TypeError):
        amount = Decimal('0.00')

    if amount <= Decimal('0.00'):
        return JsonResponse({'status': 'error', 'message': 'Invalid top-up amount.'}, status=400)

    # Perform atomic credit to user's Wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    wallet.credit(
        amount=amount,
        purpose='ADD_FUNDS',
        description=f"WALLET TOP-UP VIA RAZORPAY (PAYMENT_ID: {razorpay_payment_id})"
    )

    request.session.pop('wallet_razorpay_order_id', None)
    request.session.pop('wallet_topup_amount', None)

    wallet.refresh_from_db()
    logger.info(f"[RAZORPAY WALLET] Successfully verified & credited ₹{amount:.2f} to user #{request.user.id} wallet (Payment ID: {razorpay_payment_id}). New balance: ₹{wallet.balance:.2f}")

    messages.success(request, f"Successfully added ₹{amount:,.2f} to your Zitarra Wallet via Razorpay!")
    return JsonResponse({
        'status': 'success',
        'message': f"Successfully added ₹{amount:,.2f} to your Zitarra Wallet!",
        'amount_added': f"{amount:.2f}",
        'new_balance': f"{wallet.balance:.2f}",
        'payment_id': razorpay_payment_id,
        'redirect_url': reverse('user_wallet')
    })


@user_member_required
def add_funds_view(request):
    
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '').strip()
        try:
            amount = Decimal(amount_str)
            if amount <= Decimal('0.00'):
                messages.error(request, "Please enter a valid amount greater than ₹0.")
            elif amount > Decimal('50000.00'):
                messages.error(request, "Maximum single top-up limit is ₹50,000.00.")
            else:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.credit(
                    amount=amount,
                    purpose='ADD_FUNDS',
                    description=f"WALLET TOP-UP (MANUAL_ENTRY)"
                )
                messages.success(request, f"Successfully added ₹{amount:,.2f} to your Zitarra Wallet!")
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount entered.")

    return redirect('user_wallet')
