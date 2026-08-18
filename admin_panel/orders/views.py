from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator

from common.decorators import admin_required
from user_panel.orders.models import Order, OrderItem


STATUS_CHOICES = Order.STATUS_CHOICES


@admin_required
def admin_orders_view(request):

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort_val = request.GET.get('sort', 'Latest First').strip()
    page_num = request.GET.get('page', '1').strip()

    orders_qs = Order.objects.select_related('user').prefetch_related('items__product__images', 'items__product__category', 'items__variant__images').all()

    if search_query:
        orders_qs = orders_qs.filter(
            Q(order_id__icontains=search_query) |
            Q(shipping_full_name__icontains=search_query) |
            Q(shipping_phone__icontains=search_query) |
            Q(shipping_city__icontains=search_query) |
            Q(shipping_state__icontains=search_query) |
            Q(shipping_pincode__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__fullname__icontains=search_query) |
            Q(user__mobile_number__icontains=search_query) |
            Q(items__product_name__icontains=search_query) |
            Q(items__variant_name__icontains=search_query)
        ).distinct()


    if status_filter:
        orders_qs = orders_qs.filter(order_status=status_filter)


    if sort_val == 'Oldest First':
        orders_qs = orders_qs.order_by('created_at')
    elif sort_val == 'Amount: High to Low':
        orders_qs = orders_qs.order_by('-total_price', '-created_at')
    elif sort_val == 'Amount: Low to High':
        orders_qs = orders_qs.order_by('total_price', '-created_at')
    else:
        orders_qs = orders_qs.order_by('-created_at')


    paginator = Paginator(orders_qs, 10)
    page_obj = paginator.get_page(page_num)

    context = {
        'orders': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_val': sort_val,
        'status_choices': STATUS_CHOICES,
    }

    return render(request, 'admin_panel/orders/orders.html', context)


ALLOWED_TRANSITIONS = {
    'CONFIRMED': ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'],
    'PROCESSING': ['PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'],
    'SHIPPED': ['SHIPPED', 'DELIVERED', 'CANCELLED'],
    'DELIVERED': ['DELIVERED', 'RETURN_REQUESTED', 'RETURN_APPROVED', 'RETURN_PICKUP', 'RETURNED', 'REFUNDED'],
    'RETURN_REQUESTED': ['RETURN_REQUESTED', 'RETURN_APPROVED', 'RETURN_PICKUP', 'RETURNED', 'REFUNDED', 'DELIVERED'],
    'RETURN_APPROVED': ['RETURN_APPROVED', 'RETURN_PICKUP', 'RETURNED', 'REFUNDED'],
    'RETURN_PICKUP': ['RETURN_PICKUP', 'RETURNED', 'REFUNDED'],
    'RETURNED': ['RETURNED', 'REFUNDED'],
    'CANCELLED': ['CANCELLED'],
    'REFUNDED': ['REFUNDED'],
}


@admin_required
def admin_order_detail_view(request, order_id):

    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product__images', 'items__variant__images'),
        order_id=order_id
    )
    current_status = order.order_status
    allowed_codes = ALLOWED_TRANSITIONS.get(current_status, [code for code, _ in STATUS_CHOICES])
    allowed_choices = [(code, label) for code, label in STATUS_CHOICES if code in allowed_codes]
    is_terminal = current_status in ['CANCELLED', 'REFUNDED']

    context = {
        'order': order,
        'status_choices': allowed_choices,
        'is_terminal_status': is_terminal,
    }
    return render(request, 'admin_panel/orders/order_detail.html', context)


@admin_required
def admin_order_update_status_view(request, order_id):

    if request.method == 'POST':
        order = get_object_or_404(Order, order_id=order_id)
        new_status = request.POST.get('order_status', '').strip()
        delivery_date_str = request.POST.get('expected_delivery_date', '').strip()
        old_status = order.order_status

        # Enforce valid state transition
        allowed_statuses = ALLOWED_TRANSITIONS.get(old_status, [c[0] for c in STATUS_CHOICES])
        if new_status and new_status not in allowed_statuses:
            messages.error(request, f"Invalid Transition! An order in '{order.get_order_status_display()}' status cannot be changed to '{dict(STATUS_CHOICES).get(new_status, new_status)}'.")
            return redirect('admin_order_detail', order_id=order_id)

        with transaction.atomic():
            if delivery_date_str:
                try:
                    order.expected_delivery_date = delivery_date_str
                except Exception:
                    pass

            if new_status and new_status in allowed_statuses:
                if new_status == 'CANCELLED' and old_status != 'CANCELLED':
                    order.order_status = 'CANCELLED'
                    if not order.cancel_reason:
                        order.cancel_reason = 'Cancelled by Admin'
                    order.save()

                    # Restore stock for all non-cancelled items
                    for item in order.items.all():
                        if item.item_status != 'CANCELLED':
                            item.item_status = 'CANCELLED'
                            item.cancel_reason = 'Cancelled by Admin'
                            item.save()

                            if item.variant:
                                item.variant.stock += item.quantity
                                item.variant.save()
                            if item.product:
                                item.product.stock += item.quantity
                                item.product.save()

                    order.recalculate_totals()
                else:
                    order.order_status = new_status
                    if new_status == 'DELIVERED':
                        order.payment_status = 'PAID'
                    elif new_status in ['RETURNED', 'REFUNDED']:
                        order.payment_status = 'REFUNDED'

                    active_items = order.items.exclude(item_status='CANCELLED')
                    if not active_items.exists():
                        active_items = order.items.all()

                    new_subtotal = sum((item.item_subtotal for item in active_items), Decimal('0.00'))
                    order.subtotal = new_subtotal
                    order.tax_amount = round(new_subtotal * Decimal('0.05'), 2)
                    order.total_price = order.subtotal + order.shipping_cost + order.tax_amount - order.discount_amount
                    order.save()

                messages.success(request, f"Order #{order.order_id} updated successfully.")
            else:
                order.save()
                messages.success(request, f"Order #{order.order_id} details updated.")

    return redirect('admin_order_detail', order_id=order_id)
