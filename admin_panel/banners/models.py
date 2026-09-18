from django.db import models
from django.utils import timezone


class Banner(models.Model):
    DISPLAY_MODE_CHOICES = (
        ('HERO_SLIDER', 'Hero Slider / Carousel'),
        ('PROMO_STRIP', 'Top Promotional Strip'),
    )


    STATUS_CHOICES = (
        ('PUBLISHED', 'Published / Live'),
        ('DRAFT', 'Draft / Inactive'),
    )

    title = models.CharField(max_length=150)
    target_url = models.CharField(max_length=255, default='/shop/')
    image = models.ImageField(upload_to='banners/')
    display_mode = models.CharField(max_length=30, choices=DISPLAY_MODE_CHOICES, default='HERO_SLIDER')
    priority = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    
    impressions_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0)
    
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_display_mode_display()})"

    @property
    def clean_title(self):
        return self.title.replace('_', ' ').strip()


    @property
    def is_currently_live(self):
        if self.is_deleted or self.status != 'PUBLISHED':
            return False
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    @property
    def ctr_percentage(self):
        if self.impressions_count == 0:
            return 0.0
        return round((self.clicks_count / self.impressions_count) * 100, 1)


class ShopShowcase(models.Model):
    SLOT_CHOICES = (
        ('HERO_LEFT', 'Hero Left Banner (Top Seller)'),
        ('HERO_RIGHT', 'Hero Right Banner (Featured Flagship)'),
        ('GRID_SPOTLIGHT', 'In-Grid Spotlight (Premium Specs)'),
        ('SIDEBAR_PROMO', 'Sidebar Special Offer (Filter Drawer)'),
    )

    slot = models.CharField(max_length=30, choices=SLOT_CHOICES, unique=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='showcases')
    
    # Marketing presentation overrides
    badge_text = models.CharField(max_length=50, default="TOP SELLER")
    custom_title = models.CharField(max_length=150, blank=True, null=True, help_text="Custom display title (defaults to product name if blank)")
    subtitle = models.CharField(max_length=200, blank=True, null=True, help_text="Series name or short promotional description")
    banner_image = models.ImageField(upload_to='showcases/', blank=True, null=True, help_text="Custom dark backdrop image")
    button_label = models.CharField(max_length=50, default="SHOP MODEL")
    
    # Custom Spec Fields for GRID_SPOTLIGHT card
    spec_1_label = models.CharField(max_length=50, blank=True, default="Wattage")
    spec_1_value = models.CharField(max_length=50, blank=True, default="30 Watts RMS")
    spec_2_label = models.CharField(max_length=50, blank=True, default="Speakers")
    spec_2_value = models.CharField(max_length=50, blank=True, default="2 X 12\" Celestion")
    spec_3_label = models.CharField(max_length=50, blank=True, default="Valves")
    spec_3_value = models.CharField(max_length=50, blank=True, default="4 X EL84")
    spec_4_label = models.CharField(max_length=50, blank=True, default="Inputs")
    spec_4_value = models.CharField(max_length=50, blank=True, default="Normal & Top Boost")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shop Showcase'
        verbose_name_plural = 'Shop Showcases'

    def __str__(self):
        return f"{self.get_slot_display()} - {self.product.name}"

    @property
    def display_title(self):
        return self.custom_title.strip() if self.custom_title and self.custom_title.strip() else self.product.name

    @property
    def display_image_url(self):
        if self.banner_image:
            return self.banner_image.url
        primary_img = self.product.images.first()
        if primary_img and primary_img.image:
            return primary_img.image.url
        return ""

