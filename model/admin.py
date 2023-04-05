from django.contrib import admin
from .models import User, Notification
from .locations import Area, Table, TableStatus
from .products import Category, Allergen, ProductStatus, AvailableExtra, ContentDisclaimer, Product
from .order import Order, Session, Basket, Payment
from .device import Device


# DEVICE
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'token', 'user')


# ROLES
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'first_name')


# LOCATIONS
@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('id', 'area', 'nr', 'waiter', 'status')


@admin.register(TableStatus)
class TableStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


# PRODUCTS
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_de', 'order')


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ('id', 'code')


@admin.register(ProductStatus)
class ProductStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(AvailableExtra)
class AvailableExtraAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_de')


@admin.register(ContentDisclaimer)
class ContentDisclaimerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_de')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'new_product_nr', 'name_de', 'price', 'status')
    search_fields = ('product_nr', 'name_de')


# ORDER
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'table', 'start', 'end')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'finished', 'order_group_id')


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    # list_display = ('id', 'session')
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'method', 'total')


# NOTIFICATION
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'timestamp')




