from django.db import models
from .models import User
from .locations import Table
from .products import Product, AvailableExtra


class Session(models.Model):
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    session_nr = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Sessions'

    # def __str__(self):
    #     return str(self.session_nr)


class Order(models.Model):
    order_group_id = models.PositiveIntegerField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order_by_customer = models.BooleanField(default=False)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    chosen_extras = models.ManyToManyField(AvailableExtra, blank=True)
    gang = models.PositiveIntegerField(default=1)
    cooked = models.BooleanField(default=False)
    cook_time = models.DateTimeField(blank=True, null=True)
    finished = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Orders'

    def __str__(self):
        return str(self.id)


class Basket(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True)
    created_time = models.DateTimeField(auto_now_add=True)
    orders = models.ManyToManyField(Order, blank=True)
    finished = models.BooleanField(default=False)
    finished_time = models.DateTimeField(blank=True, null=True)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_by')
    canceled = models.BooleanField(default=False)
    canceled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='canceled_by')
    spam = models.BooleanField(default=False)
    spammed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='spammed_by')
    cooked = models.BooleanField(default=False)
    cooked_time = models.DateTimeField(blank=True, null=True)
    web_order = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Baskets'

    def __str__(self):
        return f"{self.created_time.strftime('%d.%m.%Y %H:%M')}  - Table: {self.session.table.nr} - ID: {self.id}"


class Payment(models.Model):
    customer_order = models.PositiveIntegerField(default=1)
    PAYMENTMETHODS = [
        ('cash', 'cash'),
        ('card', 'card')
    ]
    method = models.CharField(choices=PAYMENTMETHODS, max_length=200)
    orders = models.ManyToManyField(Order, blank=True)
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True)
    total = models.DecimalField(max_digits=6, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Payments'

    def __str__(self):
        return str(self.total)
