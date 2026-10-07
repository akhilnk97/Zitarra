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
        ('PARTIALLY_DELIVERED', 'Partially Delivered'),
        ('PARTIALLY_RETURNED', 'Partially Returned'),
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
            elif active_statuses.issubset({'RETURNED'}):
                self.order_status = 'RETURNED'
            elif 'DELIVERED' in active_statuses and any(s.startswith('RETURN_') or s == 'RETURNED' for s in active_statuses):
                # Mixed: delivered + returns
                if any(s.startswith('RETURN_') for s in active_statuses):
                    self.order_status = 'PARTIALLY_DELIVERED'
                else:
                    self.order_status = 'PARTIALLY_RETURNED'
            elif 'RETURN_PICKUP' in active_statuses:
                self.order_status = 'RETURN_PICKUP'
            elif 'RETURN_APPROVED' in active_statuses:
                self.order_status = 'RETURN_APPROVED'
            elif 'RETURN_REQUESTED' in active_statuses:
                self.order_status = 'RETURN_REQUESTED'
            elif 'SHIPPED' in active_statuses:
                self.order_status = 'SHIPPED'
            elif 'PROCESSING' in active_statuses:
                self.order_status = 'PROCESSING'
            elif 'CONFIRMED' in active_statuses:
                self.order_status = 'CONFIRMED'

            # Recalculate payment_status based on payment method and actual refunds
            is_cod = self.payment_method in ['CASH_ON_DELIVERY', 'COD']
            has_deliv = self.items.filter(item_status='DELIVERED').exists()
            has_returned = self.items.filter(item_status='RETURNED').exists()

            if is_cod:
                # In Cash on Delivery:
                # - Cancelled items are never paid for (no refund).
                # - Return requested/approved/pickup items have not been refunded yet.
                # - Only items with status 'RETURNED' have been accepted and refunded to the wallet.
                if has_returned:
                    if not self.items.exclude(item_status__in=['CANCELLED', 'RETURNED']).exists():
                        self.payment_status = 'REFUNDED'
                    elif has_deliv:
                        self.payment_status = 'PARTIALLY_REFUNDED'
                elif has_deliv:
                    # Delivered items were paid in cash on delivery; no return has been completed
                    self.payment_status = 'PAID'
                elif not self.items.exclude(item_status='CANCELLED').exists():
                    self.payment_status = 'CANCELLED'
                elif self.payment_status not in ['PAID', 'REFUNDED', 'PARTIALLY_REFUNDED']:
                    self.payment_status = 'PENDING'
            else:
                # In prepaid orders (Razorpay, Wallet, etc.):
                # - Cancelled items were paid upfront and refunded to wallet.
                # - Returned items were paid upfront and refunded to wallet upon completion.
                # - Return requested/approved/pickup items have NOT been refunded yet.
                has_ret_or_canc = self.items.filter(item_status__in=['CANCELLED', 'RETURNED']).exists()
                all_ret_or_canc = not self.items.exclude(item_status__in=['CANCELLED', 'RETURNED']).exists()
                if all_ret_or_canc:
                    self.payment_status = 'REFUNDED'
                elif has_ret_or_canc and (has_deliv or self.payment_status in ['PAID', 'VERIFIED', 'PARTIALLY_REFUNDED']):
                    self.payment_status = 'PARTIALLY_REFUNDED'
                elif has_deliv:
                    self.payment_status = 'PAID'
        self.save()

    @property
    def has_mixed_statuses(self):
        statuses = set(self.items.values_list('item_status', flat=True))
        return len(statuses) > 1

    @property
    def has_delivered_items(self):
        return self.items.filter(item_status='DELIVERED').exists()

    @property
    def has_returned_items(self):
        return self.items.filter(item_status='RETURNED').exists()

    @property
    def has_cancelled_items(self):
        return self.items.filter(item_status='CANCELLED').exists()

    @property
    def has_return_in_progress(self):
        return self.items.filter(item_status__in=['RETURN_REQUESTED', 'RETURN_APPROVED', 'RETURN_PICKUP']).exists()

    @property
    def is_partially_refunded(self):
        if self.payment_status == 'PARTIALLY_REFUNDED':
            return True
        is_cod = self.payment_method in ['CASH_ON_DELIVERY', 'COD']
        if is_cod:
            # In COD, it's only partially refunded if there are both delivered items AND completed returned items
            return self.has_delivered_items and self.has_returned_items
        # In prepaid, only if there are actual refunded items (CANCELLED or RETURNED) alongside remaining active items
        return self.payment_status in ['PAID', 'REFUNDED', 'PARTIALLY_REFUNDED', 'VERIFIED'] and (self.has_returned_items or self.has_cancelled_items) and self.items.exclude(item_status__in=['CANCELLED', 'RETURNED']).exists()

    @property
    def total_refunded_amount(self):
        is_cod = self.payment_method in ['CASH_ON_DELIVERY', 'COD']
        if is_cod:
            # In COD, cancelled items were never charged or paid; only delivered items that were returned got refunded
            refunded_items = self.items.filter(item_status='RETURNED')
        else:
            # In prepaid, cancelled items and completed returned items were refunded
            refunded_items = self.items.filter(item_status__in=['CANCELLED', 'RETURNED'])
        net_subtotal = sum((max(Decimal('0.00'), i.item_subtotal - i.discount_amount) for i in refunded_items), Decimal('0.00'))
        tax = round(net_subtotal * Decimal('0.05'), 2)
        return net_subtotal + tax

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

    @property
    def can_generate_invoice(self):
        """Returns True only if the order is eligible for tax invoice generation."""
        if self.order_status in ['PENDING', 'CANCELLED', 'RETURNED', 'REFUNDED'] or self.payment_status in ['FAILED', 'REFUNDED']:
            return False
        return self.items.exclude(item_status__in=['CANCELLED', 'RETURNED', 'REFUNDED']).exists()

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

    @property
    def mrp(self):
        if self.variant and self.variant.price:
            return self.variant.price
        if self.product and self.product.price:
            return self.product.price
        return self.price

    @property
    def has_offer_discount(self):
        return self.mrp > self.price

    @property
    def offer_discount_amount(self):
        if self.mrp > self.price:
            return self.mrp - self.price
        return Decimal('0.00')

    @property
    def total_offer_discount(self):
        return self.offer_discount_amount * self.quantity

    @property
    def offer_details(self):
        if not self.has_offer_discount:
            return None
        if self.product:
            eff = self.product.get_effective_discount()
            if eff.get('has_discount'):
                return {
                    'percentage': eff.get('discount_percentage'),
                    'name': eff.get('offer_name'),
                    'type': eff.get('offer_type'),
                }
        pct = round(((self.mrp - self.price) / self.mrp) * Decimal('100'))
        return {
            'percentage': pct,
            'name': 'Promotional Offer',
            'type': 'PRODUCT',
        }

    class Meta:
        ordering = ['id']

    def __str__(self):
        var_info = f" [{self.variant_name}]" if self.variant_name else ""
        return f"{self.quantity}x {self.product_name}{var_info} in Order #{self.order.order_id}"