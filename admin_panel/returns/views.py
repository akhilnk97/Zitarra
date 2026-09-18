import logging
from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from common.decorators import admin_required
from user_panel.orders.models import Order, OrderItem, Product, ProductVariant
from user_panel.wallet.models import Wallet

logger = logging.getLogger(__name__)


@admin_required
def admin_returns_management_view(request):
    search_query = request.GET.get('search', '').strip()
    status_tab = request.GET.get('tab', 'ALL').strip().upper()
    sort_val = request.GET.get('sort', 'LATEST').strip().upper()
    page_num = request.GET.get('page', '1').strip()

    items_qs = OrderItem.objects.filter(
        Q(item_status__startswith='RETURN_') |
        Q(item_status__in=['RETURNED', 'REFUNDED', 'RETURN_REJECTED']) |
        Q(cancel_reason__icontains='Return Rejected') |
        Q(admin_note__icontains='reject') |
        Q(return_images__isnull=False)
    ).select_related(
        'order', 'order__user', 'product', 'variant'
    ).prefetch_related(
        'return_images', 'product__images', 'variant__images'
    ).distinct()

    active_requests_count = items_qs.filter(item_status__in=['RETURN_REQUESTED', 'RETURN_APPROVED', 'RETURN_PICKUP']).count()
    pending_review_count = items_qs.filter(item_status='RETURN_REQUESTED').count()

    if status_tab == 'PENDING':
        items_qs = items_qs.filter(item_status='RETURN_REQUESTED')
    elif status_tab == 'APPROVED':
        items_qs = items_qs.filter(item_status__in=['RETURN_APPROVED', 'RETURN_PICKUP'])
    elif status_tab == 'COMPLETED':
        items_qs = items_qs.filter(item_status__in=['RETURNED', 'REFUNDED'])
    elif status_tab == 'REJECTED':
        items_qs = items_qs.filter(
            Q(item_status='RETURN_REJECTED') |
            Q(cancel_reason__icontains='Return Rejected') |
            Q(admin_note__icontains='reject')
        )

    if search_query:
        items_qs = items_qs.filter(
            Q(order__order_id__icontains=search_query) |
            Q(order__shipping_full_name__icontains=search_query) |
            Q(order__user__email__icontains=search_query) |
            Q(product_name__icontains=search_query) |
            Q(cancel_reason__icontains=search_query)
        ).distinct()

    sort_raw = request.GET.get('sort', 'Latest First').strip()
    sort_upper = sort_raw.upper()

    if sort_upper in ['OLDEST', 'OLDEST FIRST']:
        sort_val = 'Oldest First'
        items_qs = items_qs.order_by('id')
    elif sort_upper in ['HIGH_AMOUNT', 'AMOUNT: HIGH TO LOW']:
        sort_val = 'Amount: High to Low'
        items_qs = items_qs.order_by('-price', '-id')
    elif sort_upper in ['LOW_AMOUNT', 'AMOUNT: LOW TO HIGH']:
        sort_val = 'Amount: Low to High'
        items_qs = items_qs.order_by('price', '-id')
    else:
        sort_val = 'Latest First'
        items_qs = items_qs.order_by('-id')

    paginator = Paginator(items_qs, 10)
    page_obj = paginator.get_page(page_num)

    context = {
        'return_items': page_obj.object_list,
        'page_obj': page_obj,
        'active_requests_count': active_requests_count,
        'pending_review_count': pending_review_count,
        'status_tab': status_tab,
        'search_query': search_query,
        'sort_val': sort_val,
    }
    return render(request, 'admin_panel/orders/returns.html', context)


@admin_required
def admin_return_action_view(request, item_id):
    if request.method != 'POST':
        return redirect('admin_returns')

    item = get_object_or_404(OrderItem.objects.select_related('order', 'product', 'variant'), id=item_id)
    action = request.POST.get('action', '').strip().lower()
    admin_note = request.POST.get('admin_note', '').strip()
    pickup_date_str = request.POST.get('expected_pickup_date', '').strip()

    with transaction.atomic():
        if action == 'approve':
            item.item_status = 'RETURN_APPROVED'
            if pickup_date_str:
                try:
                    item.expected_pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d').date()
                    item.item_status = 'RETURN_PICKUP'
                except ValueError:
                    pass
            item.admin_note = admin_note or 'Return request verified and approved.'
            item.save(update_fields=['item_status', 'admin_note', 'expected_pickup_date'])
            item.order.recalculate_totals()
            messages.success(request, f"Return approved for '{item.product_name}' in Order #{item.order.order_id}.")

        elif action == 'schedule_pickup':
            if pickup_date_str:
                try:
                    item.expected_pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d').date()
                    if item.item_status in ['RETURN_REQUESTED', 'RETURN_APPROVED']:
                        item.item_status = 'RETURN_PICKUP'
                    if admin_note:
                        item.admin_note = admin_note
                    else:
                        item.admin_note = f"Pickup scheduled for {item.expected_pickup_date.strftime('%d-%m-%Y')}."
                    item.save(update_fields=['item_status', 'expected_pickup_date', 'admin_note'])
                    item.order.recalculate_totals()
                    messages.success(request, f"Expected pickup date set to {item.expected_pickup_date.strftime('%d-%m-%Y')} for '{item.product_name}'.")
                except ValueError:
                    messages.error(request, "Invalid pickup date format provided.")
            else:
                messages.error(request, "Please select an expected pickup date.")

        elif action == 'reject':
            item.item_status = 'RETURN_REJECTED'
            item.cancel_reason = f"Return Rejected: {admin_note or 'Request did not pass verification.'}"
            item.admin_note = admin_note or 'Return request rejected after inspection.'
            item.save(update_fields=['item_status', 'cancel_reason', 'admin_note'])
            item.order.recalculate_totals()
            messages.error(request, f"Return request rejected for '{item.product_name}' in Order #{item.order.order_id}.")

        elif action == 'complete':
            old_status = item.item_status
            item.item_status = 'RETURNED'
            if pickup_date_str:
                try:
                    item.expected_pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            item.admin_note = admin_note or 'Item returned and inventory updated.'
            item.save(update_fields=['item_status', 'admin_note', 'expected_pickup_date'])

            if old_status not in ['RETURNED', 'CANCELLED']:
                if item.variant_id:
                    v = ProductVariant.objects.select_for_update().get(id=item.variant_id)
                    v.stock += item.quantity
                    v.save(update_fields=['stock', 'updated_at'])
                    if v.product:
                        v.product.sync_stock_from_variants()
                elif item.product_id:
                    p = Product.objects.select_for_update().get(id=item.product_id)
                    p.stock += item.quantity
                    p.save(update_fields=['stock', 'updated_at'])

                net_item_price = max(Decimal('0.00'), item.item_subtotal - item.discount_amount)
                item_tax = round(net_item_price * Decimal('0.05'), 2)
                refund_amount = net_item_price + item_tax

                if refund_amount > Decimal('0.00'):
                    wallet, _ = Wallet.objects.get_or_create(user=item.order.user)
                    wallet.credit(
                        amount=refund_amount,
                        purpose='ORDER_RETURN_REFUND',
                        description=f"RETURN REFUND FOR '{item.product_name}' IN ORDER #{item.order.order_id}",
                        order=item.order
                    )

                item.order.payment_status = 'REFUNDED'
                item.order.save(update_fields=['payment_status'])
                item.order.recalculate_totals()

                logger.info(f"[RETURNS] Return action '{action}' executed for OrderItem #{item.id} (Order #{item.order.order_id}). Refunded ₹{refund_amount:.2f} to user #{item.order.user.id} wallet.")
                messages.success(request, f"Return completed, stock restored & ₹{refund_amount:,.2f} refunded to {item.order.user.email}'s Zitarra Wallet.")
            else:
                messages.info(request, f"Item is already marked as {old_status}.")

    return redirect('admin_returns')
