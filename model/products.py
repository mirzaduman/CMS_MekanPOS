from django.db import models


class Category(models.Model):
    name_de = models.CharField(max_length=50)
    name_tr = models.CharField(max_length=50)
    name_en = models.CharField(max_length=50)
    order = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name_de


class Allergen(models.Model):
    name_de = models.CharField(max_length=200)
    name_tr = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    code = models.CharField(max_length=30)

    class Meta:
        verbose_name_plural = 'Allergens'

    def __str__(self):
        return self.code


class ProductStatus(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = 'Product Statuses'

    def __str__(self):
        return self.name


class AvailableExtra(models.Model):
    name_de = models.CharField(max_length=50)
    name_tr = models.CharField(max_length=50)
    name_en = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        verbose_name_plural = 'Extras'

    def __str__(self):
        return self.name_de


class ContentDisclaimer(models.Model):
    name_de = models.CharField(max_length=50)
    name_tr = models.CharField(max_length=50)
    name_en = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = 'Content Disclaimers'

    def __str__(self):
        return self.name_de


class Product(models.Model):
    name_de = models.CharField(max_length=200)
    name_tr = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    product_nr = models.IntegerField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    picture = models.ImageField(upload_to='product_pictures/', blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    allergens = models.ManyToManyField(Allergen, blank=True)
    description_de = models.CharField(max_length=500, blank=True, null=True)
    description_tr = models.CharField(max_length=500, blank=True, null=True)
    description_en = models.CharField(max_length=500, blank=True, null=True)
    extras = models.ManyToManyField(AvailableExtra, blank=True)
    good_with = models.ManyToManyField('self', blank=True)
    content_disclaimer = models.ManyToManyField(ContentDisclaimer, blank=True)
    status = models.ForeignKey(ProductStatus, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.name_de
