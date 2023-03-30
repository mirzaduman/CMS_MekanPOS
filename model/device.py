from django.db import models
from .models import User


class Device(models.Model):
    token = models.CharField(max_length=1000)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
