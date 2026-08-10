from user_panel.wishlist.models import Wishlist


def wishlist_item_count(request):
    if request.user.is_authenticated:
        try:
            wishlist = request.user.wishlist
            return {'wishlist_item_count': wishlist.get_total_items()}
        except Exception:
            return {'wishlist_item_count': 0}
    return {'wishlist_item_count': 0}
