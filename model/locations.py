import uuid

from django.db import models
from .models import User


class Area(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = 'Areas'

    def __str__(self):
        return self.name


class TableStatus(models.Model):
    name = models.CharField(max_length=50)
    border_color = models.CharField(max_length=50)
    fill_color = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = 'Table Statuses'

    def __str__(self):
        return self.name


class Table(models.Model):
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True)
    nr = models.CharField(max_length=20)
    new_nr = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(TableStatus, on_delete=models.SET_NULL, null=True)
    status_change = models.DateTimeField(blank=True, null=True)
    waiter = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    table_hash = models.UUIDField(default=uuid.uuid4)

    class Meta:
        verbose_name_plural = 'Tables'

    def __str__(self):
        return self.nr


