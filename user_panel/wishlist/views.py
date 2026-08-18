from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator

from common.decorators import user_member_required
from admin_panel.products.models import Product, ProductVariant
from user_panel.cart.models import Cart, CartItem
from .models import Wishlist, WishlistItem


@user_member_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    all_items = wishlist.items.select_related('product', 'variant', 'product__category').all()
    
    paginator = Paginator(all_items, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    from_profile = request.GET.get('from') == 'profile'

    context = {
        'wishlist': wishlist,
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'total_items': all_items.count(),
        'from_profile': from_profile,
    }
    return render(request, 'user/wishlist/wishlist.html', context)


@user_member_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
    variant_id = request.POST.get('variant_id') or request.GET.get('variant_id')
    variant = None
    if variant_id:
        variant = ProductVariant.objects.filter(id=variant_id, product=product, is_active=True).first()

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    existing_item = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()

    if existing_item:
        existing_item.delete()
        messages.success(request, f"{product.name} removed from your wishlist.")
    else:
        WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            variant=variant
        )
        messages.success(request, f"{product.name} added to your wishlist.")

    redirect_url = request.META.get('HTTP_REFERER') or 'wishlist:wishlist_view'
    return redirect(redirect_url)


@user_member_required
def remove_from_wishlist(request, product_id):
    wishlist = Wishlist.objects.filter(user=request.user).first()
    if wishlist:
        WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).delete()
        messages.success(request, "Item removed from your wishlist.")

    return redirect('wishlist:wishlist_view')


@user_member_required
def move_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)

    if product.stock == 0:
        messages.error(request, f"{product.name} is currently out of stock.")
        return redirect('wishlist:wishlist_view')

    with transaction.atomic():
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if not created:
            if cart_item.quantity < min(CartItem.MAX_QUANTITY, product.stock):
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f"Increased quantity of {product.name} in cart.")
            else:
                messages.warning(request, f"Maximum limit reached for {product.name}.")
        else:
            messages.success(request, f"{product.name} moved to cart.")

        WishlistItem.objects.filter(wishlist__user=request.user, product=product).delete()

    return redirect('wishlist:wishlist_view')
