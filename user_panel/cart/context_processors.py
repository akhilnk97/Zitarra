from user_panel.cart.models import Cart

def cart_item_count(request):
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            return {'cart_item_count': cart.get_total_items()}
        except Exception:
            return {'cart_item_count': 0}
    return {'cart_item_count': 0}
