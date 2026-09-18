from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from common.decorators import user_member_required
from django.contrib import messages

from .models import Cart, CartItem
from admin_panel.products.models import Product, ProductVariant
from user_panel.wishlist.models import WishlistItem
from common.services import calculate_order_totals, is_ajax
from decimal import Decimal
from user_panel.orders.models import Coupon
from user_panel.wishlist.models import Wishlist, WishlistItem


@user_member_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product__category', 'variant').all()
    has_out_of_stock = any(item.is_available and item.stock == 0 for item in items)
    has_unavailable = any(not item.is_available for item in items)
    subtotal = cart.get_subtotal()
    applied_coupon_code = request.session.get('applied_coupon')
    discount_amount = Decimal('0.00')
    applied_coupon = None

    if applied_coupon_code:
        coupon = Coupon.objects.filter(code__iexact=applied_coupon_code, is_active=True).first()
        if coupon:
            disc = coupon.calculate_discount(subtotal)
            if disc > Decimal('0.00'):
                discount_amount = disc
                applied_coupon = coupon
            else:
                request.session.pop('applied_coupon', None)
        else:
            request.session.pop('applied_coupon', None)

    shipping_cost, tax_amount, total_price = calculate_order_totals(subtotal, discount_amount)
    context = {
        'cart': cart,
        'items': items,
        'has_out_of_stock': has_out_of_stock,
        'has_unavailable': has_unavailable,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'applied_coupon': applied_coupon,
        'shipping_cost': shipping_cost,
        'tax_amount': tax_amount,
        'total_price': total_price,
    }
    return render(request, 'user/cart/cart.html', context)


@user_member_required
def add_to_cart(request, product_id):
    if request.method != 'POST':
        return redirect('cart_view')

    product = get_object_or_404(Product, id=product_id)

    if not product.is_available:
        msg = "This product is no longer available."
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': msg})
        messages.error(request, msg)
        return redirect('shop')

    variant_id = request.POST.get('variant_id', '').strip()
    variant = None

    if variant_id and variant_id != 'base':
        try:
            variant = ProductVariant.objects.get(id=variant_id, product=product, is_active=True, is_deleted=False)
        except ProductVariant.DoesNotExist:
            variant = None

    # If product has active variants and none was explicitly passed (e.g. from shop quick-add card), pick the first active in-stock variant
    active_variants = product.variants.filter(is_active=True, is_deleted=False)
    if active_variants.exists():
        if not variant:
            in_stock_var = active_variants.filter(stock__gt=0).order_by('id').first()
            variant = in_stock_var or active_variants.first()

    available_stock = variant.stock if variant else product.stock

    if available_stock == 0:
        item_title = f"{product.name} ({variant.name})" if variant else product.name
        msg = f"'{item_title}' is currently out of stock."
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': msg})
        messages.error(request, msg)
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('shop')

    try:
        qty_requested = int(request.POST.get('quantity', 1))
        if qty_requested < 1:
            qty_requested = 1
    except (ValueError, TypeError):
        qty_requested = 1

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)
    var_suffix = f" ({variant.name})" if variant else ""

    if not created:
        new_qty = item.quantity + qty_requested
        if item.quantity >= CartItem.MAX_QUANTITY or new_qty > CartItem.MAX_QUANTITY:
            msg = f"Maximum limit of {CartItem.MAX_QUANTITY} units per product reached."
            if is_ajax(request):
                return JsonResponse({'status': 'warning', 'message': msg})
            messages.warning(request, msg)
            referer = request.META.get('HTTP_REFERER')
            return redirect(referer or 'shop')

        elif new_qty > available_stock:
            msg = f"Cannot add {qty_requested} more. Only {available_stock} units available in stock."
            if is_ajax(request):
                return JsonResponse({'status': 'warning', 'message': msg})
            messages.warning(request, msg)
            referer = request.META.get('HTTP_REFERER')
            return redirect(referer or 'shop')

        else:
            item.quantity = new_qty
            item.save()
            msg = f"{product.name}{var_suffix} (x{qty_requested}) added to cart"
            WishlistItem.objects.filter(wishlist__user=request.user, product=product).delete()
            if is_ajax(request):
                return JsonResponse({'status': 'success', 'message': msg, 'cart_count': cart.get_total_items()})
            messages.success(request, msg)
            
    else:
        actual_qty = min(qty_requested, available_stock, CartItem.MAX_QUANTITY)
        item.quantity = actual_qty
        item.save()
        msg = f"{product.name}{var_suffix} (x{actual_qty}) added to cart"
        WishlistItem.objects.filter(wishlist__user=request.user, product=product).delete()
        if is_ajax(request):
            return JsonResponse({'status': 'success', 'message': msg, 'cart_count': cart.get_total_items()})
        messages.success(request, msg)

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('shop')


@user_member_required
def remove_from_cart(request, item_id):
    if request.method != 'POST':
        return redirect('cart_view')

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = item.product.name
    if item.variant:
        product_name += f" ({item.variant.name})"
    item.delete()
    messages.success(request, f"{product_name} removed from cart.")
    return redirect('cart_view')


@user_member_required
def update_quantity(request, item_id, action):
    if request.method != 'POST':
        if is_ajax(request):
            return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)
        return redirect('cart_view')

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    status_type = 'success'
    message_text = 'Quantity updated.'

    if action == 'increment':
        if item.quantity >= CartItem.MAX_QUANTITY:
            status_type = 'warning'
            message_text = f"Maximum {CartItem.MAX_QUANTITY} items allowed per product."
            if not is_ajax(request):
                messages.warning(request, message_text)
        elif item.quantity >= item.stock:
            status_type = 'warning'
            message_text = f"Only {item.stock} units available in stock."
            if not is_ajax(request):
                messages.warning(request, message_text)
        else:
            item.quantity += 1
            item.save()
            if not is_ajax(request):
                messages.success(request, message_text)

    elif action == 'decrement':
        if item.quantity <= 1:
            item.delete()
            status_type = 'removed'
            message_text = "Item removed from cart."
            if not is_ajax(request):
                messages.success(request, message_text)
        else:
            item.quantity -= 1
            item.save()
            if not is_ajax(request):
                messages.success(request, message_text)

    cart = request.user.cart
    cart_subtotal = cart.get_subtotal()
    cart_total_items = cart.get_total_items()
    items_count = cart.items.count()
    has_out_of_stock = any(i.stock == 0 for i in cart.items.select_related('product', 'variant').all())
    shipping_cost, tax_amount, total_price = calculate_order_totals(cart_subtotal)

    if is_ajax(request):
        shipping_label = "FREE" if (cart_subtotal > 0 and shipping_cost == 0) else f"₹{shipping_cost:,.2f}"
        return JsonResponse({
            'status': status_type,
            'message': message_text,
            'item_id': item_id,
            'quantity': item.quantity if status_type != 'removed' else 0,
            'item_subtotal': f"{item.get_subtotal():,.2f}" if status_type != 'removed' else "0.00",
            'item_price': f"{item.get_unit_price():,.2f}" if status_type != 'removed' else "0.00",
            'cart_subtotal': f"{cart_subtotal:,.2f}",
            'shipping_cost': f"{shipping_cost:,.2f}",
            'shipping_label': shipping_label,
            'tax_amount': f"{tax_amount:,.2f}",
            'total_price': f"{total_price:,.2f}",
            'cart_total_items': cart_total_items,
            'items_count': items_count,
            'has_out_of_stock': has_out_of_stock,
        })

@user_member_required
def move_to_wishlist(request, item_id):
    if request.method != 'POST':
        return redirect('cart_view')

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product = item.product
    variant = item.variant
    product_name = product.name
    if variant:
        product_name += f" ({variant.name})"


    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    WishlistItem.objects.get_or_create(wishlist=wishlist, product=product, variant=variant)

    item.delete()
    messages.success(request, f"{product_name} moved to your wishlist.")
    return redirect('cart_view')

