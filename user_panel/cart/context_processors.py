from user_panel.cart.models import Cart


def cart_item_count(request):
    """
    Context processor to make the total cart item count available globally
    across all templates as {{ cart_item_count }}.
    """
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            return {'cart_item_count': cart.get_total_items()}
        except Exception:
            return {'cart_item_count': 0}
    return {'cart_item_count': 0}
