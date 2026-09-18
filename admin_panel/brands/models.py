from django.db import models
from django.utils.text import slugify


class Brand(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active Now'),
        ('PENDING', 'Pending Review'),
        ('SUSPENDED', 'Suspended'),
    )

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='brands/logos/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def product_count(self):
        return self.products.filter(is_active=True, is_deleted=False).count() if hasattr(self, 'products') else 0
