from decimal import Decimal
from django.db import models


class Coupon(models.Model):
    DISCOUNT_TYPES = (
        ('PERCENTAGE', 'Percentage Discount'),
        ('FIXED', 'Fixed Amount Discount'),
    )

    OFFER_TYPES = (
        ('GENERAL', 'General Cart Offer'),
        ('CATEGORY_SPECIFIC', 'Category-Specific Offer'),
        ('PRODUCT_SPECIFIC', 'Product-Specific Offer'),
        ('REFERRAL', 'Referral Offer'),
    )

    code = models.CharField(max_length=50, unique=True)
    campaign_name = models.CharField(max_length=100, blank=True, default='')
    offer_type = models.CharField(max_length=30, choices=OFFER_TYPES, default='GENERAL')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='PERCENTAGE')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_limit_per_user = models.PositiveIntegerField(default=1, null=True, blank=True, help_text="Max redemptions per user")
    is_first_order_only = models.BooleanField(default=False, help_text="Restricted to new users with 0 prior orders")
    applicable_categories = models.ManyToManyField('category.Category', blank=True, related_name='applicable_coupons')
    applicable_products = models.ManyToManyField('products.Product', blank=True, related_name='applicable_coupons')
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders_coupon'

    @property
    def status_code(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return 'DISABLED'
        if self.valid_from and now < self.valid_from:
            return 'SCHEDULED'
        if self.valid_to and now > self.valid_to:
            return 'EXPIRED'
        if self.usage_limit and self.used_count >= self.usage_limit:
            return 'EXPIRED'
        return 'ACTIVE'

    def calculate_discount(self, subtotal, cart_items=None):
        from django.utils import timezone
        now = timezone.now()
        subtotal = Decimal(str(subtotal))

        if not self.is_active:
            return Decimal('0.00')
        if self.valid_from and now < self.valid_from:
            return Decimal('0.00')
        if self.valid_to and now > self.valid_to:
            return Decimal('0.00')
        if self.usage_limit and self.used_count >= self.usage_limit:
            return Decimal('0.00')

        qualifying_subtotal = subtotal

        if self.offer_type == 'CATEGORY_SPECIFIC' and cart_items:
            cat_ids = set(self.applicable_categories.values_list('id', flat=True))
            if cat_ids:
                qualifying_subtotal = Decimal('0.00')
                for item in cart_items:
                    item_cat_id = getattr(item.product, 'category_id', None)
                    if item_cat_id in cat_ids:
                        item_price = item.get_subtotal() if hasattr(item, 'get_subtotal') else getattr(item, 'total_price', Decimal('0.00'))
                        qualifying_subtotal += Decimal(str(item_price))
        elif self.offer_type == 'PRODUCT_SPECIFIC' and cart_items:
            prod_ids = set(self.applicable_products.values_list('id', flat=True))
            if prod_ids:
                qualifying_subtotal = Decimal('0.00')
                for item in cart_items:
                    item_prod_id = getattr(item.product, 'id', None)
                    if item_prod_id in prod_ids:
                        item_price = item.get_subtotal() if hasattr(item, 'get_subtotal') else getattr(item, 'total_price', Decimal('0.00'))
                        qualifying_subtotal += Decimal(str(item_price))

        if qualifying_subtotal < self.min_purchase or qualifying_subtotal <= Decimal('0.00'):
            return Decimal('0.00')

        if self.discount_type == 'PERCENTAGE':
            disc = (qualifying_subtotal * (self.discount_value / Decimal('100.00'))).quantize(Decimal('0.01'))
            if self.max_discount and disc > self.max_discount:
                disc = self.max_discount
            return disc
        else:
            return min(self.discount_value, qualifying_subtotal)

    def __str__(self):
        return f"Coupon {self.code} ({self.discount_value}{'%' if self.discount_type == 'PERCENTAGE' else ' INR'})"
