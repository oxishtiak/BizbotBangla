from django.db import models
from django.contrib.auth.models import User

class Shop(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    shop_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.shop_name

class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    stock = models.FloatField(default=0)
    unit = models.CharField(max_length=50, default='পিস')
    buy_price = models.FloatField(default=0)
    sell_price = models.FloatField(default=0)
    low_stock_alert = models.FloatField(default=0)
    def __str__(self): return self.name

    @property
    def is_low_stock(self):
        if self.stock <= 0:
            return True
        if self.low_stock_alert <= 0:
            return False
        return self.stock <= self.low_stock_alert

    @property
    def profit_per_unit(self):
        return round(self.sell_price - self.buy_price, 2)

class Transaction(models.Model):
    TYPE_CHOICES = [('sell','বিক্রয়'),('buy','ক্রয়')]
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='transactions')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.TextField()
    quantity = models.FloatField(default=0)
    unit_price = models.FloatField(default=0)
    total_amount = models.FloatField()
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-date','-created_at']
    def __str__(self): return f"{self.get_transaction_type_display()} ৳{self.total_amount}"

class Baki(models.Model):
    shop     = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='bakis')
    name     = models.CharField(max_length=200)
    amount   = models.FloatField()
    note     = models.TextField(blank=True)
    date     = models.DateField()
    # ✅ কোন পণ্য বাকিতে গেছে
    product  = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-date','-created_at']
    def __str__(self): return f"{self.name} — ৳{self.amount}"