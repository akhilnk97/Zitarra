from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime

from common.decorators import admin_required
from user_panel.orders.models import Order, OrderItem
from admin_panel.products.models import ProductVariant, Product

STATUS_CHOICES = Order.STATUS_CHOICES


@admin_required
def admin_orders_view(request):

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort_val = request.GET.get('sort', 'Latest First').strip()
    page_num = request.GET.get('page', '1').strip()

    orders_qs = Order.objects.select_related('user').prefetch_related('items__product__images', 'items__product__category', 'items__variant__images').all()

    if search_query:
        q_objects = (
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
        )
        words = search_query.split()
        if len(words) > 1:
            word_q = Q()
            for w in words:
                word_q &= (
                    Q(order_id__icontains=w) |
                    Q(shipping_full_name__icontains=w) |
                    Q(shipping_phone__icontains=w) |
                    Q(user__email__icontains=w) |
                    Q(user__fullname__icontains=w) |
                    Q(items__product_name__icontains=w) |
                    Q(items__variant_name__icontains=w)
                )
            q_objects |= word_q

        orders_qs = orders_qs.filter(q_objects).distinct()


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

    # Auto-align future expected delivery dates to today's date when order is DELIVERED
    if order.order_status == 'DELIVERED':
        today = timezone.now().date()
        if order.expected_delivery_date and order.expected_delivery_date > today:
            order.expected_delivery_date = today
            order.save(update_fields=['expected_delivery_date'])
        for item in order.items.filter(item_status='DELIVERED'):
            if item.expected_delivery_date and item.expected_delivery_date > today:
                item.expected_delivery_date = today
                item.save(update_fields=['expected_delivery_date'])

    current_status = order.order_status
    allowed_codes = ALLOWED_TRANSITIONS.get(current_status, [code for code, _ in STATUS_CHOICES])
    allowed_choices = [(code, label) for code, label in STATUS_CHOICES if code in allowed_codes]
    is_terminal = current_status in ['DELIVERED', 'CANCELLED', 'RETURN_REQUESTED', 'RETURN_APPROVED', 'RETURN_PICKUP', 'RETURNED', 'REFUNDED']

    context = {
        'order': order,
        'status_choices': allowed_choices,
        'all_status_choices': STATUS_CHOICES,
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

        # Date Validation
        parsed_delivery_date = None
        if delivery_date_str:
            try:
                parsed_delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date()
                today = timezone.now().date()
                if parsed_delivery_date < today:
                    messages.error(request, f"Invalid Delivery Date! Expected delivery date ({parsed_delivery_date.strftime('%d/%m/%Y')}) cannot be in the past.")
                    return redirect('admin_order_detail', order_id=order_id)
            except ValueError:
                messages.error(request, "Invalid Date Format! Please enter a valid date in YYYY-MM-DD format.")
                return redirect('admin_order_detail', order_id=order_id)
        elif new_status and new_status not in ['CANCELLED', 'REFUNDED'] and not order.expected_delivery_date:
            messages.error(request, "Expected delivery date is required when updating order status.")
            return redirect('admin_order_detail', order_id=order_id)

        with transaction.atomic():
            if parsed_delivery_date:
                order.expected_delivery_date = parsed_delivery_date
                for item in order.items.exclude(item_status='CANCELLED'):
                    if item.item_status.startswith('RETURN_') or item.item_status == 'RETURNED':
                        item.expected_pickup_date = parsed_delivery_date
                        item.save(update_fields=['expected_pickup_date'])
                    else:
                        item.expected_delivery_date = parsed_delivery_date
                        item.save(update_fields=['expected_delivery_date'])

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
                    today = timezone.now().date()
                    if new_status == 'DELIVERED':
                        order.payment_status = 'PAID'
                        order.expected_delivery_date = today
                    elif new_status == 'RETURNED':
                        order.payment_status = 'REFUNDED'
                        order.expected_delivery_date = today

                    # Update all active items to new status and update dates
                    for item in order.items.exclude(item_status='CANCELLED'):
                        item.item_status = new_status
                        update_fields = ['item_status']
                        if new_status == 'DELIVERED':
                            item.expected_delivery_date = today
                            update_fields.append('expected_delivery_date')
                        elif new_status in ['RETURN_PICKUP', 'RETURNED']:
                            item.expected_pickup_date = today
                            update_fields.append('expected_pickup_date')
                        item.save(update_fields=update_fields)

                    order.save()
                    order.recalculate_totals()

                messages.success(request, f"Order #{order.order_id} updated successfully.")
            else:
                order.save()
                messages.success(request, f"Order #{order.order_id} details updated.")

    return redirect('admin_order_detail', order_id=order_id)


@admin_required
def admin_order_item_update_status_view(request, order_id, item_id):
    if request.method == 'POST':
        item = get_object_or_404(OrderItem, id=item_id, order__order_id=order_id)
        new_status = request.POST.get('item_status', '').strip()
        delivery_date_str = request.POST.get('expected_delivery_date', '').strip()

        if item.is_terminal and new_status and new_status != item.item_status:
            messages.error(request, f"Cannot update status! Product '{item.product_name}' is in terminal '{item.get_item_status_display()}' status.")
            return redirect('admin_order_detail', order_id=order_id)

        if new_status and new_status not in item.allowed_transitions:
            messages.error(request, f"Invalid status transition! Product '{item.product_name}' in '{item.get_item_status_display()}' status cannot be changed to '{dict(STATUS_CHOICES).get(new_status, new_status)}'.")
            return redirect('admin_order_detail', order_id=order_id)

        # Date Validation
        parsed_date = None
        target_status = new_status or item.item_status
        if delivery_date_str:
            try:
                parsed_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date()
                today = timezone.now().date()
                if parsed_date < today:
                    label = "Pickup date" if (target_status.startswith('RETURN_') or target_status == 'RETURNED') else "Expected delivery date"
                    messages.error(request, f"Invalid Date! {label} ({parsed_date.strftime('%d/%m/%Y')}) cannot be in the past.")
                    return redirect('admin_order_detail', order_id=order_id)
            except ValueError:
                messages.error(request, "Invalid Date Format! Please enter a valid date.")
                return redirect('admin_order_detail', order_id=order_id)

        elif target_status not in ['CANCELLED', 'REFUNDED']:
            existing_date = item.expected_pickup_date if (target_status.startswith('RETURN_') or target_status == 'RETURNED') else item.expected_delivery_date
            if not existing_date:
                messages.error(request, "Expected date is required when updating product status.")
                return redirect('admin_order_detail', order_id=order_id)

        with transaction.atomic():
            if parsed_date:
                if target_status.startswith('RETURN_') or target_status == 'RETURNED':
                    item.expected_pickup_date = parsed_date
                else:
                    item.expected_delivery_date = parsed_date
                    item.order.expected_delivery_date = parsed_date
                    item.order.save(update_fields=['expected_delivery_date'])

            if new_status and new_status != item.item_status:
                old_status = item.item_status
                item.item_status = new_status
                if new_status in ['RETURNED', 'DELIVERED', 'RETURN_PICKUP']:
                    if new_status in ['RETURNED', 'RETURN_PICKUP']:
                        item.expected_pickup_date = timezone.now().date()
                    else:
                        item.expected_delivery_date = timezone.now().date()

                if new_status == 'CANCELLED' and old_status != 'CANCELLED':
                    item.cancel_reason = 'Cancelled by Admin'
                    if item.variant_id:
                        v = ProductVariant.objects.select_for_update().get(id=item.variant_id)
                        v.stock += item.quantity
                        v.save(update_fields=['stock'])

                    elif item.product_id:
                        p = Product.objects.select_for_update().get(id=item.product_id)
                        p.stock += item.quantity
                        p.save(update_fields=['stock'])

            item.save()
            item.order.recalculate_totals()
            messages.success(request, f"Item '{item.product_name}' updated successfully.")

    return redirect('admin_order_detail', order_id=order_id)

