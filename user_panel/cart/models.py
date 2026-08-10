from django.db import models
from user_panel.authentication.models import User
from admin_panel.products.models import Product


class Cart(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def get_subtotal(self):
        return sum(item.get_subtotal() for item in self.items.all())

    def get_total_items(self):
        return self.items.count()

    def __str__(self):
        return f"Cart of {self.user.fullname}"


class CartItem(models.Model):

    MAX_QUANTITY = 10

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart}"
