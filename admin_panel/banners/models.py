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
    target_url = models.CharField(max_length=255, default='/shop/', help_text="Redirect path e.g. /shop/, /shop/?category=Guitars")
    image = models.ImageField(upload_to='banners/')
    display_mode = models.CharField(max_length=30, choices=DISPLAY_MODE_CHOICES, default='HERO_SLIDER')
    priority = models.IntegerField(default=1, help_text="Order priority (01, 02, etc.)")
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
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'

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
