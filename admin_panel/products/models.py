from django.db import models
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
    highlights = models.TextField(blank=True, null=True, help_text="Product highlights separated by newlines")

    def __str__(self):
        return self.name

    @property
    def stock_info(self):
        if self.stock == 0:
            return {"status": "out_of_stock", "label": "Out of Stock", "is_out": True}
        elif self.stock <= 5:
            return {"status": "low_stock", "label": f"Only {self.stock} Left", "is_out": False}
        return {"status": "in_stock", "label": "In Stock", "is_out": False}


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=7, default="#FFFFFF")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

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
