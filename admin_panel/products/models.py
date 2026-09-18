from django.db import models
from django.conf import settings
from admin_panel.category.models import Category


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    offer = models.CharField(max_length=100, blank=True, null=True)
    product_offer = models.ForeignKey('offers.ProductOffer', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    highlights = models.TextField(blank=True, null=True, help_text="Product highlights separated by newlines")

    def __str__(self):
        return self.name

    def get_effective_discount(self):
        """
        Determines the best available discount (Product Offer vs Category Offer).
        Returns a dict:
        {
            'has_discount': bool,
            'discount_percentage': int,
            'offer_type': 'PRODUCT' | 'CATEGORY' | None,
            'offer_name': str
        }
        """
        prod_disc = 0
        prod_offer_name = ""
        if self.product_offer and self.product_offer.is_valid:
            prod_disc = self.product_offer.discount_percentage
            prod_offer_name = self.product_offer.name

        cat_disc = 0
        cat_offer_name = ""
        if self.category and getattr(self.category, 'is_offer_valid', False):
            cat_disc = self.category.discount
            cat_offer_name = f"{self.category.name} Offer"

        if prod_disc >= cat_disc and prod_disc > 0:
            return {
                'has_discount': True,
                'discount_percentage': prod_disc,
                'offer_type': 'PRODUCT',
                'offer_name': prod_offer_name
            }
        elif cat_disc > 0:
            return {
                'has_discount': True,
                'discount_percentage': cat_disc,
                'offer_type': 'CATEGORY',
                'offer_name': cat_offer_name
            }
        return {
            'has_discount': False,
            'discount_percentage': 0,
            'offer_type': None,
            'offer_name': ''
        }

    def get_discounted_price(self, base_price=None):
        from decimal import Decimal
        if base_price is None:
            var = self.variants.filter(is_active=True, is_deleted=False).first()
            base_price = var.price if (var and var.price) else self.price
        base = Decimal(str(base_price))
        eff = self.get_effective_discount()
        if eff['has_discount']:
            disc_amt = (base * Decimal(str(eff['discount_percentage']))) / Decimal('100')
            return round(base - disc_amt, 2)
        return base

    @property
    def is_available(self):
        return (
            self.is_active and
            not self.is_deleted and
            self.category is not None and
            self.category.is_active and
            not self.category.is_deleted
        )

    @property
    def has_active_variants(self):
        return self.variants.filter(is_active=True, is_deleted=False).exists()

    @property
    def total_stock(self):
        active_vars = self.variants.filter(is_active=True, is_deleted=False)
        if active_vars.exists():
            return sum(v.stock for v in active_vars)
        return self.stock

    def sync_stock_from_variants(self):
        """Synchronizes parent product.stock to the sum of all active variant stocks."""
        active_vars = self.variants.filter(is_active=True, is_deleted=False)
        if active_vars.exists():
            new_stock = sum(v.stock for v in active_vars)
            if self.stock != new_stock:
                self.stock = new_stock
                self.save(update_fields=['stock', 'updated_at'])
            return new_stock
        return self.stock

    @property
    def is_completely_out_of_stock(self):
        return self.total_stock == 0

    @property
    def stock_info(self):
        current_stock = self.total_stock if self.has_active_variants else self.stock
        if current_stock == 0:
            return {"status": "out_of_stock", "label": "Out of Stock", "is_out": True}
        elif current_stock <= 5:
            return {"status": "low_stock", "label": f"Only {current_stock} Left", "is_out": False}
        return {"status": "in_stock", "label": "In Stock", "is_out": False}


    @property
    def average_rating(self):
        avg = self.reviews.aggregate(models.Avg('rating'))['rating__avg']
        return round(avg, 1) if avg is not None else None

    @property
    def total_reviews_count(self):
        return self.reviews.count()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=7, default="#FFFFFF")
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    def generate_sku(self):
        """Generates a professional unique SKU for this variant."""
        brand_code = (self.product.brand or 'ZTR').upper()[:3]
        cat_code = (self.product.category.name or 'CAT').upper()[:3] if self.product.category else 'CAT'
        prod_id = self.product.id or 0
        var_id = self.id or 0
        color_slug = ''.join(e for e in self.name.upper() if e.isalnum())[:3] or 'CLR'
        return f"{brand_code}-{cat_code}-{prod_id:04d}-{var_id:02d}-{color_slug}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not self.sku:
            self.sku = self.generate_sku()
            super().save(update_fields=['sku'])

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.price

    def get_discounted_price(self):
        return self.product.get_discounted_price(base_price=self.effective_price)

    @property
    def stock_info(self):
        if self.stock == 0:
            return {"status": "out_of_stock", "label": "Out of Stock", "is_out": True}
        elif self.stock <= 5:
            return {"status": "low_stock", "label": f"Only {self.stock} Left", "is_out": False}
        return {"status": "in_stock", "label": "In Stock", "is_out": False}


class VariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='variants/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.variant.name}"


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    reviewer_name = models.CharField(max_length=100)

    rating = models.IntegerField(default=5)
    title = models.CharField(max_length=200)
    comment = models.TextField()
    image = models.ImageField(upload_to='reviews/images/', blank=True, null=True)
    video = models.FileField(upload_to='reviews/videos/', blank=True, null=True)
    is_verified_buyer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reviewer_name} ({self.rating}★) - {self.product.name}"

