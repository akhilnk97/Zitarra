from django.db import models
from django.conf import settings

class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    pincode = models.CharField(max_length=20)
    badge = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'DEFAULT'
    is_default = models.BooleanField(default=False)
    label = models.CharField(max_length=20, default='HOME')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if not Address.objects.filter(user=self.user).exists():
            self.is_default = True

        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False, badge='')
            self.badge = 'DEFAULT'
        else:
            if self.badge == 'DEFAULT':
                self.badge = ''
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.address_line_1}"


class Referral(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Sign-up'),
        ('REGISTERED', 'Registered'),
        ('COMPLETED', 'First Purchase Completed'),
        ('EXPIRED', 'Expired'),
    )

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_by_relation')
    referral_code = models.CharField(max_length=50)
    token = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reward_credited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders_referral'

    def __str__(self):
        return f"Referral {self.referral_code} by {self.referrer.username} -> {self.referred_user.username if self.referred_user else 'Pending'}"
