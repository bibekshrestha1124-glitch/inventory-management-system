from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField('SKU', max_length=50, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10, help_text='Product is "low stock" at or below this quantity.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def get_absolute_url(self):
        return reverse('inventory:product_detail', args=[self.pk])

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def stock_value(self):
        return self.quantity * self.cost_price


class InsufficientStock(ValueError):
    pass


class StockMovement(models.Model):
    IN = 'IN'
    OUT = 'OUT'
    TYPE_CHOICES = [(IN, 'Stock In'), (OUT, 'Stock Out')]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.get_movement_type_display()} {self.quantity} x {self.product.name}'


def apply_movement(product, movement_type, quantity, user=None, supplier=None, note=''):
    """Create a StockMovement and update product quantity atomically."""
    if quantity < 1:
        raise ValueError('Quantity must be at least 1.')
    with transaction.atomic():
        locked = Product.objects.select_for_update().get(pk=product.pk)
        if movement_type == StockMovement.OUT:
            if quantity > locked.quantity:
                raise InsufficientStock(f'Only {locked.quantity} unit(s) of {locked.name} in stock.')
            locked.quantity -= quantity
        else:
            locked.quantity += quantity
        locked.save(update_fields=['quantity', 'updated_at'])
        return StockMovement.objects.create(
            product=locked, movement_type=movement_type, quantity=quantity,
            supplier=supplier, note=note, created_by=user,
        )
