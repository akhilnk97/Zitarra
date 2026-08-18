from django.db import models
from user_panel.authentication.models import User
from admin_panel.products.models import Product, ProductVariant


class Cart(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def get_subtotal(self):
        return sum(item.get_subtotal() for item in self.items.all() if item.is_available)

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all() if item.is_available)

    def __str__(self):
        return f"Cart of {self.user.fullname}"


class CartItem(models.Model):

    MAX_QUANTITY = 5

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    def get_unit_price(self):
        if self.variant and self.variant.price:
            return self.variant.price
        return self.product.price

    def get_subtotal(self):
        return self.get_unit_price() * self.quantity

    def __str__(self):
        variant_str = f" ({self.variant.name})" if self.variant else ""
        return f"{self.quantity}x {self.product.name}{variant_str} in {self.cart}"

