from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    def __str__(self):
        return f'Username: {self.username}'

class Order(models.Model):
    ticker = models.CharField(max_length=5)
    side = models.CharField(max_length=3)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    time = models.DateTimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    class Meta:
        unique_together = ['ticker', 'side', 'quantity', 'price', 'time', 'user']
    def __str__(self):
        return f"{self.user.username} {'bought'if self.side == 'Buy' else 'sold'} {self.quantity} share(s) of {self.ticker} on {self.time}"