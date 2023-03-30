from django.db import models
from django.contrib.auth.models import AbstractUser

# from .order import Session


class User(AbstractUser):
    phone = models.CharField(max_length=50, blank=True, null=True)
    is_manager = models.BooleanField(default=False)
    is_waiter_chef = models.BooleanField(default=False)
    is_waiter = models.BooleanField(default=False)
    pin = models.PositiveIntegerField(null=True, blank=True)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    # session = models.ForeignKey('model.Session', on_delete=models.SET_NULL, null=True)
    log = models.TextField(blank=True, null=True)
    action_made = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    assigned_basket = models.ForeignKey('model.Basket', on_delete=models.SET_NULL, null=True)

