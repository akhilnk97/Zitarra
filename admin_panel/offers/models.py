from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class ProductOffer(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_percentage = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        help_text="Percentage discount between 1% and 99%"
    )
    start_date = models.DateField(blank=True, null=True, help_text="Offer start date (optional)")
    end_date = models.DateField(blank=True, null=True, help_text="Offer expiry date (optional)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product Offer'
        verbose_name_plural = 'Product Offers'

    def __str__(self):
        return f"{self.name} ({self.discount_percentage}% OFF)"

    @property
    def is_valid(self):
        if not self.is_active or not self.discount_percentage or self.discount_percentage <= 0:
            return False
        today = timezone.now().date()
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

    @property
    def status_code(self):
        if not self.is_active:
            return 'DISABLED'
        today = timezone.now().date()
        if self.start_date and today < self.start_date:
            return 'SCHEDULED'
        if self.end_date and today > self.end_date:
            return 'EXPIRED'
        return 'ACTIVE'

    @property
    def products_count(self):
        return self.products.filter(is_deleted=False).count()
