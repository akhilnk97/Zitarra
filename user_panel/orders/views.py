from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db import transaction
from common.decorators import user_member_required
from user_panel.cart.models import Cart
from user_panel.profiles.models import Address
from admin_panel.products.models import Product
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
    orders_list = Order.objects.filter(user=request.user).prefetch_related(
        'items__product__images', 'items__variant__images'
    ).order_by('-created_at')

    query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if query:
        orders_list = orders_list.filter(
            Q(order_id__icontains=query) |
            Q(items__product_name__icontains=query)
        ).distinct()

    if status_filter:
        orders_list = orders_list.filter(order_status=status_filter)

    paginator = Paginator(orders_list, 10)
    page = request.GET.get('page', 1)
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    context = {
        'orders': orders,
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
        if order.order_status == 'DELIVERED' and order.payment_status != 'PAID':
            order.payment_status = 'PAID'
        
        # If all items were marked cancelled but order is active/delivered, restore items
        if order.items.filter(item_status='CANCELLED').count() == order.items.count() and order.items.exists():
            order.items.update(item_status='CONFIRMED', cancel_reason=None)
        
        active_items = order.items.exclude(item_status='CANCELLED')
        if active_items.exists():
            new_subtotal = sum(item.item_subtotal for item in active_items)
            if order.subtotal == Decimal('0.00') or order.total_price == Decimal('0.00') or order.subtotal != new_subtotal:
                order.subtotal = new_subtotal
                order.tax_amount = round(new_subtotal * Decimal('0.05'), 2)
                order.total_price = order.subtotal + order.shipping_cost + order.tax_amount - order.discount_amount
                order.save()

    return render(request, 'user/orders/order_detail.html', {'order': order})


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
                order.order_status = 'RETURN_REQUESTED'
                order.return_reason = reason
                order.save()

            messages.success(request, f"Return request submitted for Order #{order.order_id}. Our team will review your request shortly.")
        else:
            messages.error(request, "Return requests can only be submitted for delivered orders.")

    return redirect('order_detail', order_id=order_id)


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
                            item.variant.save()
                        if item.product:
                            item.product.stock += item.quantity
                            item.product.save()

                order.recalculate_totals()

            messages.success(request, f"Order #{order.order_id} has been cancelled successfully.")
        else:
            messages.error(request, "This order cannot be cancelled at its current status.")

    return redirect('order_detail', order_id=order_id)