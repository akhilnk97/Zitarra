from django.db import models
from django.conf import settings
from admin_panel.products.models import Product, ProductVariant


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wishlist ({self.user.email})"

    def get_total_items(self):
        return self.items.count()


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='wishlist_items')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product', 'variant')
        ordering = ['-created_at']

    @property
    def stock_info(self):
        if self.variant:
            return self.variant.stock_info
        return self.product.stock_info

    @property
    def is_available(self):
        if not self.product.is_available:
            return False
        if self.variant:
            if not self.variant.is_active or self.variant.is_deleted:
                return False
        return True

    @property
    def stock(self):
        if self.variant:
            return self.variant.stock
        return self.product.stock

    def __str__(self):
        variant_str = f" ({self.variant.name})" if self.variant else ""
        return f"{self.product.name}{variant_str} in {self.wishlist.user.email}'s wishlist"
