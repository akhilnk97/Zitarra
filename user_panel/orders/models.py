from decimal import Decimal
from django.db import models
from django.conf import settings
from admin_panel.products.models import Product, ProductVariant
import random
import string
from datetime import timedelta
from django.utils import timezone
from user_panel.returns.models import ReturnRequestImage
from user_panel.coupons.models import Coupon
from user_panel.profiles.models import Referral

def generate_order_id():
    """Generates unique Order ID like ZT-99281"""
    num = ''.join(random.choices(string.digits, k=5))
    return f"ZT-{num}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURN_APPROVED', 'Return Approved'),
        ('RETURN_PICKUP', 'Pickup Scheduled'),
        ('RETURNED', 'Returned'),
        ('RETURN_REJECTED', 'Return Rejected'),
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

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    cancel_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)

    expected_delivery_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def recalculate_totals(self):
        """Recalculates order subtotal, tax, and total price after item cancellations, and updates summary order status."""
        active_items = self.items.exclude(item_status='CANCELLED')
        if not active_items.exists():
            self.order_status = 'CANCELLED'
            if not self.cancel_reason:
                self.cancel_reason = 'All items in order were cancelled.'
            self.subtotal = Decimal('0.00')
            self.tax_amount = Decimal('0.00')
            self.total_price = Decimal('0.00')
        else:
            new_subtotal = sum((item.item_subtotal for item in active_items), Decimal('0.00'))
            self.subtotal = new_subtotal
            self.discount_amount = sum((item.discount_amount for item in active_items), Decimal('0.00'))

            discounted_subtotal = max(Decimal('0.00'), self.subtotal - self.discount_amount)
            self.tax_amount = round(discounted_subtotal * Decimal('0.05'), 2)
            calc_total = discounted_subtotal + self.shipping_cost + self.tax_amount
            self.total_price = max(Decimal('0.00'), calc_total)

            # Recalculate summary order_status based on active items
            active_statuses = set(active_items.values_list('item_status', flat=True))
            if active_statuses == {'DELIVERED'}:
                self.order_status = 'DELIVERED'
            elif 'RETURN_REQUESTED' in active_statuses:
                self.order_status = 'RETURN_REQUESTED'
            elif 'RETURN_APPROVED' in active_statuses:
                self.order_status = 'RETURN_APPROVED'
            elif 'RETURN_PICKUP' in active_statuses:
                self.order_status = 'RETURN_PICKUP'
            elif active_statuses.issubset({'RETURNED'}):
                self.order_status = 'RETURNED'
            elif 'SHIPPED' in active_statuses:
                self.order_status = 'SHIPPED'
            elif 'PROCESSING' in active_statuses:
                self.order_status = 'PROCESSING'
            elif 'CONFIRMED' in active_statuses:
                self.order_status = 'CONFIRMED'
        self.save()

    @property
    def default_delivery_date(self):
        active_items = self.items.exclude(item_status='CANCELLED')
        return_items = [i for i in active_items if i.item_status.startswith('RETURN_') or i.item_status == 'RETURNED']
        if return_items:
            pickup_dates = [i.expected_pickup_date for i in return_items if i.expected_pickup_date]
            if pickup_dates:
                return min(pickup_dates)
            effective_dates = [i.effective_expected_pickup_date for i in return_items if i.effective_expected_pickup_date]
            if effective_dates:
                return min(effective_dates)
        item_dates = [i.expected_delivery_date for i in active_items if i.expected_delivery_date]
        if item_dates:
            return min(item_dates)
        if self.expected_delivery_date:
            return self.expected_delivery_date
        if self.created_at:

            return (self.created_at + timedelta(days=5)).date()

        return (timezone.now() + timedelta(days=5)).date()

    def __str__(self):
        return f"Order {self.order_id}"


class OrderItem(models.Model):
    ITEM_STATUS_CHOICES = Order.STATUS_CHOICES

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    item_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    item_status = models.CharField(max_length=50, choices=ITEM_STATUS_CHOICES, default='CONFIRMED')
    cancel_reason = models.TextField(blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    expected_delivery_date = models.DateField(blank=True, null=True)
    expected_pickup_date = models.DateField(blank=True, null=True)

    @property
    def effective_status(self):
        return self.item_status

    @property
    def effective_status_display(self):
        return self.get_item_status_display()

    @property
    def effective_expected_delivery_date(self):
        if self.expected_delivery_date:
            return self.expected_delivery_date
        return self.order.default_delivery_date

    @property
    def effective_expected_pickup_date(self):
        if self.expected_pickup_date:
            return self.expected_pickup_date
        from datetime import timedelta
        deliv_date = self.effective_expected_delivery_date
        if deliv_date:
            return deliv_date + timedelta(days=3)
        from django.utils import timezone
        return timezone.now().date() + timedelta(days=3)

    @property
    def allowed_transitions(self):
        transitions = {
            'CONFIRMED': ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'],
            'PROCESSING': ['PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'],
            'SHIPPED': ['SHIPPED', 'DELIVERED', 'CANCELLED'],
            'DELIVERED': ['DELIVERED'],
            'RETURN_REQUESTED': ['RETURN_REQUESTED'],
            'RETURN_APPROVED': ['RETURN_APPROVED'],
            'RETURN_PICKUP': ['RETURN_PICKUP'],
            'RETURNED': ['RETURNED'],
            'CANCELLED': ['CANCELLED'],
        }
        return transitions.get(self.item_status, [self.item_status])

    @property
    def is_terminal(self):
        return self.item_status in ['CANCELLED', 'RETURNED']

    class Meta:
        ordering = ['id']

    def __str__(self):
        var_info = f" [{self.variant_name}]" if self.variant_name else ""
        return f"{self.quantity}x {self.product_name}{var_info} in Order #{self.order.order_id}"