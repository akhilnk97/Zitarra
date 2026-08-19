from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db import transaction
from common.decorators import user_member_required
from user_panel.cart.models import Cart
from user_panel.profiles.models import Address
from admin_panel.products.models import Product, ProductVariant
from common.services import (
    validate_full_name,
    validate_phone_number,
    validate_pincode,
    validate_city,
    validate_state,
    validate_address_line,
    calculate_order_totals,
    is_ajax,
)
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Order, OrderItem


@user_member_required
def checkout_view(request):
    try:
        cart = request.user.cart
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)
    
    items = cart.items.select_related('product__category', 'variant').all()
    if not items.exists():
        return redirect('cart_view')

    for item in items:
        if not item.is_available:
            messages.error(request, f"'{item.product.name}' is currently unavailable. Please remove it from your cart to proceed.")
            return redirect('cart_view')

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first() or addresses.first()

    subtotal = cart.get_subtotal()
    shipping_cost, tax_amount, total_price = calculate_order_totals(subtotal)

    context = {
        'cart': cart,
        'items': items,
        'addresses': addresses,
        'default_address': default_address,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax_amount': tax_amount,
        'total_price': total_price,
    }
    return render(request, 'user/checkout/checkout.html', context)


@user_member_required
def place_order_view(request):
    if request.method != 'POST':
        return redirect('checkout')

    try:
        cart = request.user.cart
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty.")
        return redirect('cart_view')
    
    items = cart.items.select_related('product__category', 'variant').all()
    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart_view')

    # Verify inventory stock and availability for all items
    for item in items:
        if not item.is_available:
            messages.error(request, f"Product '{item.product.name}' is no longer available.")
            return redirect('cart_view')

        if item.quantity > item.stock:
            item_label = f"{item.product.name} ({item.variant.name})" if item.variant else item.product.name
            messages.error(request, f"Not enough stock for '{item_label}'. Only {item.stock} left.")
            return redirect('cart_view')

    selected_address_id = request.POST.get('selected_address')
    if not selected_address_id:
        messages.error(request, "Please select a shipping address.")
        return redirect('checkout')

    try:
        address = Address.objects.get(id=selected_address_id, user=request.user)
    except Address.DoesNotExist:
        messages.error(request, "Selected address was not found.")
        return redirect('checkout')

    payment_method = request.POST.get('payment_method', 'CASH_ON_DELIVERY').upper()
    if payment_method != 'CASH_ON_DELIVERY':
        messages.error(request, "Only Cash on Delivery is currently supported.")
        return redirect('checkout')
    
    subtotal = cart.get_subtotal()
    shipping_cost, tax_amount, calculated_total = calculate_order_totals(subtotal)
    discount_amount = Decimal('0.00')
    total_price = calculated_total - discount_amount

    payment_status = 'PENDING'

    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone_number,
            shipping_address_line_1=address.address_line_1,
            shipping_address_line_2=address.address_line_2 or '',
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_pincode=address.pincode,
            shipping_label=address.label or 'HOME',
            payment_method=payment_method,
            payment_status=payment_status,
            order_status='CONFIRMED',
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_price=total_price,
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                variant_name=item.variant.name if item.variant else None,
                price=item.get_unit_price(),
                quantity=item.quantity,
                item_subtotal=item.get_subtotal(),
            )

            if item.variant:
                item.variant.stock -= item.quantity
                item.variant.save(update_fields=['stock'])
            else:
                item.product.stock -= item.quantity
                item.product.save(update_fields=['stock'])

        cart.items.all().delete()

    return redirect('order_success', order_id=order.order_id)


@user_member_required
def checkout_add_address_view(request):
    if request.method != 'POST':
        return redirect('checkout')

    if Address.objects.filter(user=request.user).count() >= 3:
        msg = "Maximum limit of 3 saved addresses reached. You can edit any existing address."
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('checkout')

    full_name = request.POST.get('full_name', '').strip().upper()
    phone_number = request.POST.get('phone_number', '').strip().upper()
    address_line_1 = request.POST.get('address_line_1', '').strip().upper()
    address_line_2 = request.POST.get('address_line_2', '').strip().upper()
    city = request.POST.get('city', '').strip().upper()
    state = request.POST.get('state', '').strip().upper()
    pincode = request.POST.get('pincode', '').strip().upper()
    label = request.POST.get('label', 'HOME').strip().upper()
    is_default = request.POST.get('is_default') in ['true', 'on', '1']

    if not full_name or not phone_number or not address_line_1 or not city or not state or not pincode:
        msg = "All required address fields must be filled."
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('checkout')

    error = (
        validate_full_name(full_name) or
        validate_phone_number(phone_number) or
        validate_pincode(pincode) or
        validate_address_line(address_line_1) or
        validate_city(city) or
        validate_state(state)
    )
    if error:
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': error}, status=400)
        messages.error(request, error)
        return redirect('checkout')

    if is_default:
        Address.objects.filter(user=request.user).update(is_default=False, badge='')

    badge_val = 'DEFAULT' if is_default else ''

    Address.objects.create(
        user=request.user,
        full_name=full_name,
        phone_number=phone_number,
        address_line_1=address_line_1,
        address_line_2=address_line_2 or None,
        city=city,
        state=state,
        pincode=pincode,
        is_default=is_default,
        badge=badge_val,
        label=label,
    )

    msg = "Shipping address added successfully!"
    messages.success(request, msg)
    if is_ajax(request):
        return JsonResponse({'status': 'success', 'message': msg})

    return redirect('checkout')


@user_member_required
def checkout_edit_address_view(request, address_id):
    if request.method != 'POST':
        return redirect('checkout')

    address = get_object_or_404(Address, id=address_id, user=request.user)

    full_name = request.POST.get('full_name', '').strip().upper()
    phone_number = request.POST.get('phone_number', '').strip().upper()
    address_line_1 = request.POST.get('address_line_1', '').strip().upper()
    address_line_2 = request.POST.get('address_line_2', '').strip().upper()
    city = request.POST.get('city', '').strip().upper()
    state = request.POST.get('state', '').strip().upper()
    pincode = request.POST.get('pincode', '').strip().upper()
    label = request.POST.get('label', 'HOME').strip().upper()
    is_default = request.POST.get('is_default') in ['true', 'on', '1']

    if not full_name or not phone_number or not address_line_1 or not city or not state or not pincode:
        msg = "All required address fields must be filled."
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('checkout')

    error = (
        validate_full_name(full_name) or
        validate_phone_number(phone_number) or
        validate_pincode(pincode) or
        validate_address_line(address_line_1) or
        validate_city(city) or
        validate_state(state)
    )
    if error:
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': error}, status=400)
        messages.error(request, error)
        return redirect('checkout')

    if is_default and not address.is_default:
        Address.objects.filter(user=request.user).update(is_default=False, badge='')

    address.full_name = full_name
    address.phone_number = phone_number
    address.address_line_1 = address_line_1
    address.address_line_2 = address_line_2 or None
    address.city = city
    address.state = state
    address.pincode = pincode
    address.is_default = is_default
    address.badge = 'DEFAULT' if is_default else ''
    address.label = label
    address.save()

    msg = "Shipping address updated successfully!"
    messages.success(request, msg)
    if is_ajax(request):
        return JsonResponse({'status': 'success', 'message': msg})

    return redirect('checkout')


@user_member_required
def order_success_view(request, order_id):
    # Consume any pending session messages so they don't leak on back-button navigation
    list(get_messages(request))
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product__images', 'items__variant__images'),
        order_id=order_id,
        user=request.user
    )
    return render(request, 'user/checkout/order_success.html', {'order': order})


@user_member_required
def my_orders_view(request):
    items_list = OrderItem.objects.filter(
        order__user=request.user
    ).select_related(
        'order', 'product', 'variant'
    ).prefetch_related(
        'product__images', 'variant__images'
    ).order_by('-order__created_at', '-id')

    query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if query:
        q_objects = (
            Q(order__order_id__icontains=query) |
            Q(product_name__icontains=query) |
            Q(variant_name__icontains=query) |
            Q(product__name__icontains=query) |
            Q(product__description__icontains=query) |
            Q(product__category__name__icontains=query)
        )
        words = query.split()
        if len(words) > 1:
            word_q = Q()
            for w in words:
                word_q &= (
                    Q(order__order_id__icontains=w) |
                    Q(product_name__icontains=w) |
                    Q(variant_name__icontains=w) |
                    Q(product__name__icontains=w) |
                    Q(product__description__icontains=w) |
                    Q(product__category__name__icontains=w)
                )
            q_objects |= word_q

        items_list = items_list.filter(q_objects).distinct()

    if status_filter:
        items_list = items_list.filter(item_status=status_filter)

    paginator = Paginator(items_list, 10)
    page = request.GET.get('page', 1)
    try:
        order_items = paginator.page(page)
    except PageNotAnInteger:
        order_items = paginator.page(1)
    except EmptyPage:
        order_items = paginator.page(paginator.num_pages)

    context = {
        'orders': order_items,
        'order_items': order_items,
        'search_query': query,
        'status_filter': status_filter,
    }
    return render(request, 'user/orders/my_orders.html', context)


@user_member_required
def order_detail_view(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related('items__product__images', 'items__variant__images'),
        order_id=order_id,
        user=request.user
    )
    if order.order_status != 'CANCELLED':
        from django.utils import timezone
        today = timezone.now().date()
        if order.order_status == 'DELIVERED':
            if order.payment_status != 'PAID':
                order.payment_status = 'PAID'
            if order.expected_delivery_date and order.expected_delivery_date > today:
                order.expected_delivery_date = today
            order.save()
            for item in order.items.filter(item_status='DELIVERED'):
                if item.expected_delivery_date and item.expected_delivery_date > today:
                    item.expected_delivery_date = today
                    item.save(update_fields=['expected_delivery_date'])
        
        order.recalculate_totals()

    item_id = request.GET.get('item_id') or request.GET.get('item')
    selected_item = None
    if item_id:
        selected_item = order.items.filter(id=item_id).first()

    if selected_item:
        order_items = [selected_item]
        display_subtotal = selected_item.item_subtotal
        display_tax = round(display_subtotal * Decimal('0.05'), 2)
        display_shipping = order.shipping_cost if order.items.exclude(item_status='CANCELLED').count() <= 1 else Decimal('0.00')
        display_total = display_subtotal + display_tax + display_shipping
    else:
        order_items = list(order.items.all())
        display_subtotal = order.subtotal
        display_tax = order.tax_amount
        display_shipping = order.shipping_cost
        display_total = order.total_price

    context = {
        'order': order,
        'order_items': order_items,
        'selected_item': selected_item,
        'display_subtotal': display_subtotal,
        'display_tax': display_tax,
        'display_shipping': display_shipping,
        'display_total': display_total,
    }
    return render(request, 'user/orders/order_detail.html', context)


@user_member_required
def cancel_order_item_view(request, order_id, item_id):
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if not next_url:
        from django.urls import reverse
        next_url = reverse('order_detail', kwargs={'order_id': order_id})

    if request.method != 'POST':
        return redirect(next_url)

    order_item = get_object_or_404(
        OrderItem.objects.select_related('order', 'product', 'variant'),
        id=item_id,
        order__order_id=order_id,
        order__user=request.user
    )

    if order_item.item_status != 'CONFIRMED' or order_item.order.order_status not in ['CONFIRMED', 'PROCESSING', 'SHIPPED']:
        messages.error(request, "This item cannot be cancelled at its current status.")
        return redirect(next_url)

    reason_select = request.POST.get('cancel_reason_select', '').strip()
    reason_text = request.POST.get('cancel_reason', '').strip()
    reason = reason_select
    if reason_select == 'Other' or not reason:
        reason = reason_text or "Cancelled by customer"
    elif reason_text and reason_text != reason_select:
        reason = f"{reason_select}: {reason_text}"

    with transaction.atomic():
        item = OrderItem.objects.select_for_update().get(id=order_item.id)

        if item.item_status == 'CANCELLED':
            messages.error(request, "This item has already been cancelled.")
            return redirect(next_url)

        item.item_status = 'CANCELLED'
        item.cancel_reason = reason
        item.save(update_fields=['item_status', 'cancel_reason'])

        if item.variant_id:
            variant = ProductVariant.objects.select_for_update().get(id=item.variant_id)
            variant.stock += item.quantity
            variant.save(update_fields=['stock'])
        elif item.product_id:
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock += item.quantity
            product.save(update_fields=['stock'])

        order_item.order.recalculate_totals()

    messages.success(request, f"Product '{order_item.product_name}' from Order #{order_item.order.order_id} has been cancelled successfully.")
    return redirect(next_url)


@user_member_required
def return_order_view(request, order_id):

    if request.method == 'POST':
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if order.order_status == 'DELIVERED':
            reason_select = request.POST.get('return_reason_select', '').strip()
            reason_text = request.POST.get('return_reason', '').strip()
            
            reason = reason_select
            if reason_select == 'Other' or not reason:
                reason = reason_text or "Return requested by customer"
            elif reason_text:
                reason = f"{reason_select}: {reason_text}"

            with transaction.atomic():
                from datetime import timedelta
                order.order_status = 'RETURN_REQUESTED'
                order.return_reason = reason
                order.save()

                for item in order.items.all():
                    if item.item_status not in ['CANCELLED', 'RETURNED']:
                        item.item_status = 'RETURN_REQUESTED'
                        item.cancel_reason = reason
                        item.expected_pickup_date = item.effective_expected_delivery_date + timedelta(days=3)
                        item.save(update_fields=['item_status', 'cancel_reason', 'expected_pickup_date'])

            messages.success(request, f"Return request submitted for Order #{order.order_id}. Our team will review your request shortly.")
        else:
            messages.error(request, "Return requests can only be submitted for delivered orders.")

    return redirect('order_detail', order_id=order_id)


@user_member_required
def return_order_item_view(request, order_id, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id, order__order_id=order_id, order__user=request.user)
    next_url = request.META.get('HTTP_REFERER') or reverse('order_detail', kwargs={'order_id': order_id})

    if request.method == 'POST':
        if order_item.item_status == 'DELIVERED':
            reason_select = request.POST.get('return_reason_select', '').strip()
            reason_text = request.POST.get('return_reason', '').strip()
            
            reason = reason_select
            if reason_select == 'Other' or not reason:
                reason = reason_text or "Return requested by customer"
            elif reason_text:
                reason = f"{reason_select}: {reason_text}"

            with transaction.atomic():
                from datetime import timedelta
                order_item.item_status = 'RETURN_REQUESTED'
                order_item.cancel_reason = reason
                order_item.expected_pickup_date = order_item.effective_expected_delivery_date + timedelta(days=3)
                order_item.save(update_fields=['item_status', 'cancel_reason', 'expected_pickup_date'])
                order_item.order.recalculate_totals()

            messages.success(request, f"Return request submitted for '{order_item.product_name}'.")
        else:
            messages.error(request, "Only delivered products can be returned.")

    return redirect(next_url)


@user_member_required
def order_invoice_view(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variant'),
        order_id=order_id,
        user=request.user
    )
    half_tax = round(order.tax_amount / Decimal('2.0'), 2)
    context = {
        'order': order,
        'half_tax': half_tax,
    }
    return render(request, 'user/orders/order_invoice.html', context)


@user_member_required
def cancel_order_view(request, order_id):

    if request.method == 'POST':
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if order.order_status in ['CONFIRMED', 'PROCESSING', 'SHIPPED']:
            reason = request.POST.get('cancel_reason', '').strip()

            with transaction.atomic():
                order.order_status = 'CANCELLED'
                order.cancel_reason = reason
                order.save()

                for item in order.items.all():
                    if item.item_status != 'CANCELLED':
                        item.item_status = 'CANCELLED'
                        item.cancel_reason = reason
                        item.save()

                        # Restore stock
                        if item.variant:
                            item.variant.stock += item.quantity
                            item.variant.save(update_fields=['stock'])
                        if item.product:
                            item.product.stock += item.quantity
                            item.product.save(update_fields=['stock'])

                order.recalculate_totals()

            messages.success(request, f"Order #{order.order_id} has been cancelled successfully.")
        else:
            messages.error(request, "This order cannot be cancelled at its current status.")

    return redirect('order_detail', order_id=order_id)