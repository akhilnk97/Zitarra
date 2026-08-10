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
