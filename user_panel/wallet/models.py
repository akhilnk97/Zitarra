from decimal import Decimal
from django.db import models
from django.conf import settings
from user_panel.orders.models import Order


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def credit(self, amount, purpose='ADMIN_CREDIT', description='', order=None):
        amt = Decimal(str(amount))
        if amt <= Decimal('0.00'):
            return None
        self.balance += amt
        self.save(update_fields=['balance', 'updated_at'])
        trx = WalletTransaction.objects.create(
            wallet=self,
            amount=amt,
            transaction_type='CREDIT',
            purpose=purpose,
            description=description,
            order=order,
            balance_after=self.balance
        )
        return trx

    def debit(self, amount, purpose='ORDER_PAYMENT', description='', order=None):
        amt = Decimal(str(amount))
        if amt <= Decimal('0.00'):
            return None
        if self.balance < amt:
            raise ValueError("Insufficient wallet balance.")
        self.balance -= amt
        self.save(update_fields=['balance', 'updated_at'])
        trx = WalletTransaction.objects.create(
            wallet=self,
            amount=amt,
            transaction_type='DEBIT',
            purpose=purpose,
            description=description,
            order=order,
            balance_after=self.balance
        )
        return trx

    @property
    def account_id(self):
        return f"ZTR-{self.user.id:04d}-X"

    def __str__(self):
        return f"Wallet for {self.user.username} (₹{self.balance:,.2f})"


class WalletTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    )

    PURPOSE_CHOICES = (
        ('ORDER_CANCELLATION_REFUND', 'Order Cancellation Refund'),
        ('ORDER_RETURN_REFUND', 'Order Return Refund'),
        ('ORDER_PAYMENT', 'Order Payment'),
        ('ADD_FUNDS', 'Add Funds'),
        ('ADMIN_CREDIT', 'Admin Manual Credit'),
        ('ADMIN_DEBIT', 'Admin Manual Debit'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES, default='ORDER_PAYMENT')
    description = models.CharField(max_length=255, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='wallet_transactions')
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    @property
    def transaction_code(self):
        return f"KZTR-TRX-{self.id:05d}"

    def __str__(self):
        return f"{self.transaction_code} - {self.transaction_type} ₹{self.amount:,.2f}"
