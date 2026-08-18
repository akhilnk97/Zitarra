from decimal import Decimal
from django.db import models
from django.conf import settings
from admin_panel.products.models import Product, ProductVariant
import random
import string


def generate_order_id():
    """Generates unique Order ID like ZT-99281"""
    num = ''.join(random.choices(string.digits, k=5))
    return f"ZT-{num}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURN_APPROVED', 'Return Approved'),
        ('RETURN_PICKUP', 'Item Picked Up'),
        ('RETURNED', 'Returned'),
        ('REFUNDED', 'Refunded'),
    )

    order_id = models.CharField(max_length=50, unique=True, default=generate_order_id)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')

    shipping_full_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=15)
    shipping_address_line_1 = models.CharField(max_length=100)
    shipping_address_line_2 = models.CharField(max_length=100, blank=True, null=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)
    shipping_label = models.CharField(max_length=50, default='HOME')

    payment_method = models.CharField(max_length=50, default='CASH_ON_DELIVERY')
    payment_status = models.CharField(max_length=50, default='VERIFIED')
    order_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='CONFIRMED')
    expected_delivery_date = models.DateField(blank=True, null=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    cancel_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def recalculate_totals(self):
        """Recalculates order subtotal, tax, and total price after item cancellations."""
        active_items = self.items.exclude(item_status='CANCELLED')
        if not active_items.exists():
            self.order_status = 'CANCELLED'
            self.subtotal = Decimal('0.00')
            self.tax_amount = Decimal('0.00')
            self.total_price = Decimal('0.00')
        else:
            new_subtotal = sum((item.item_subtotal for item in active_items), Decimal('0.00'))
            self.subtotal = new_subtotal
            self.tax_amount = round(new_subtotal * Decimal('0.05'), 2)
            self.total_price = self.subtotal + self.shipping_cost + self.tax_amount - self.discount_amount
        self.save()

    def __str__(self):
        return f"Order {self.order_id}"


class OrderItem(models.Model):
    ITEM_STATUS_CHOICES = (
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    item_subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    item_status = models.CharField(max_length=50, choices=ITEM_STATUS_CHOICES, default='CONFIRMED')
    cancel_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        var_info = f" [{self.variant_name}]" if self.variant_name else ""
        return f"{self.quantity}x {self.product_name}{var_info} in Order #{self.order.order_id}"