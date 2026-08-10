from django.shortcuts import render, get_object_or_404, redirect
from common.decorators import user_member_required
from django.contrib import messages

from .models import Cart, CartItem
from admin_panel.products.models import Product
from user_panel.wishlist.models import WishlistItem


@user_member_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product').all()
    has_out_of_stock = any(item.product.stock == 0 for item in items)
    context = {
        'cart': cart,
        'items': items,
        'has_out_of_stock': has_out_of_stock,
    }
    return render(request, 'user/cart/cart.html', context)

@user_member_required
def add_to_cart(request, product_id):
    if request.method != 'POST':
        return redirect('cart_view')

    product = get_object_or_404(Product, id=product_id)


    if not product.is_active or product.is_deleted:
        messages.error(request, "This product is not available.")
        return redirect('shop')


    if product.stock == 0:
        messages.error(request, "This product is out of stock.")
        return redirect('product_detail', product_id=product_id)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        if item.quantity >= CartItem.MAX_QUANTITY:
            messages.warning(request, "Maximum quantity limit reached.")
        elif item.quantity >= product.stock:
            messages.warning(request, "Not enough stock available.")
        else:
            item.quantity += 1
            item.save()
            messages.success(request, "Quantity updated.")
    else:
        messages.success(request, f"{product.name} added to cart.")

    WishlistItem.objects.filter(wishlist__user=request.user, product=product).delete()

    return redirect('cart_view')

@user_member_required
def remove_from_cart(request, item_id):
    if request.method != 'POST':
        return redirect('cart_view')

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = item.product.name
    item.delete()
    messages.success(request, f"{product_name} removed from cart.")
    return redirect('cart_view')

@user_member_required
def update_quantity(request, item_id, action):
    if request.method != 'POST':
        return redirect('cart_view')

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if action == 'increment':
        if item.quantity >= CartItem.MAX_QUANTITY:
            messages.warning(request, f"Maximum {CartItem.MAX_QUANTITY} items allowed.")
        elif item.quantity >= item.product.stock:
            messages.warning(request, "No more stock available.")
        else:
            item.quantity += 1
            item.save()

    elif action == 'decrement':
        if item.quantity <= 1:
            item.delete()
            messages.success(request, "Item removed from cart.")
        else:
            item.quantity -= 1
            item.save()

    return redirect('cart_view')
