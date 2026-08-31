from django.db import models


class ReturnRequestImage(models.Model):
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.CASCADE, related_name='return_images')
    image = models.ImageField(upload_to='returns/proofs/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders_returnrequestimage'

    def __str__(self):
        return f"Return Image #{self.id} for OrderItem #{self.order_item_id}"
