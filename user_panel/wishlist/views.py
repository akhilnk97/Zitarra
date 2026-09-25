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
    all_items = wishlist.items.select_related('product', 'variant', 'product__category', 'product__product_offer').all()
    
    paginator = Paginator(all_items, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    for item in page_obj.object_list:
        base_price = item.variant.price if (item.variant and item.variant.price) else item.product.price
        eff = item.product.get_effective_discount()
        item.base_price = base_price
        item.has_discount = eff['has_discount']
        item.discount_percentage = eff['discount_percentage']
        item.discounted_price = item.product.get_discounted_price(base_price) if eff['has_discount'] else base_price
        item.offer_name = eff.get('offer_name', '')

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
    if variant_id and variant_id != 'base':
        try:
            variant = ProductVariant.objects.get(id=variant_id, product=product, is_active=True, is_deleted=False)
        except ProductVariant.DoesNotExist:
            variant = None
    elif not variant_id and product.has_active_variants:
        variant = product.variants.filter(is_active=True, is_deleted=False).order_by('id').first()

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    existing_item = WishlistItem.objects.filter(wishlist=wishlist, product=product, variant=variant).first()
    var_suffix = f" ({variant.name})" if variant else ""

    if existing_item:
        existing_item.delete()
        messages.success(request, f"{product.name}{var_suffix} removed from your wishlist.")
    else:
        WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            variant=variant
        )
        messages.success(request, f"{product.name}{var_suffix} added to your wishlist.")

    redirect_url = request.META.get('HTTP_REFERER') or 'wishlist:wishlist_view'
    return redirect(redirect_url)


@user_member_required
def remove_from_wishlist(request, product_id):
    wishlist = Wishlist.objects.filter(user=request.user).first()
    if wishlist:
        variant_id = request.POST.get('variant_id') or request.GET.get('variant_id')
        if variant_id and variant_id != 'base':
            WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id, variant_id=variant_id).delete()
        else:
            WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).delete()
        messages.success(request, "Item removed from your wishlist.")

    from_profile = request.GET.get('from') == 'profile'
    redirect_url = 'wishlist:wishlist_view'
    if from_profile:
        return redirect(f"{redirect_url}?from=profile")
    return redirect(redirect_url)


@user_member_required
def move_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
    variant_id = request.POST.get('variant_id') or request.GET.get('variant_id')
    
    wishlist_item = None
    if variant_id and variant_id != 'base':
        wishlist_item = WishlistItem.objects.filter(wishlist__user=request.user, product=product, variant_id=variant_id).first()
        variant = wishlist_item.variant if wishlist_item else ProductVariant.objects.filter(id=variant_id, product=product, is_active=True, is_deleted=False).first()
    else:
        wishlist_item = WishlistItem.objects.filter(wishlist__user=request.user, product=product).first()
        variant = wishlist_item.variant if wishlist_item else None

    var_suffix = f" ({variant.name})" if variant else ""
    available_stock = variant.stock if variant else product.stock

    if available_stock == 0:
        messages.error(request, f"'{product.name}{var_suffix}' is currently out of stock.")
        redirect_url = 'wishlist:wishlist_view'
        if request.POST.get('from') == 'profile':
            return redirect(f"{redirect_url}?from=profile")
        return redirect(redirect_url)

    with transaction.atomic():
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)

        if not created:
            if cart_item.quantity < min(CartItem.MAX_QUANTITY, available_stock):
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f"Increased quantity of {product.name}{var_suffix} in cart.")
            else:
                messages.warning(request, f"Maximum limit reached for {product.name}{var_suffix}.")
        else:
            messages.success(request, f"{product.name}{var_suffix} moved to cart.")

        if wishlist_item:
            wishlist_item.delete()
        else:
            WishlistItem.objects.filter(wishlist__user=request.user, product=product, variant=variant).delete()

    if request.POST.get('from') == 'profile':
        return redirect('/wishlist/?from=profile')
    return redirect('cart_view')
