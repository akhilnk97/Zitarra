from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    discount = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    expiry_date = models.DateField(blank=True, null=True)
    is_offer_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_offer_valid(self):
        if not self.is_offer_active or not self.discount or self.discount <= 0:
            return False
        if self.expiry_date:
            from django.utils import timezone
            if self.expiry_date < timezone.now().date():
                return False
        return True
