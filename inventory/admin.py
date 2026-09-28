from django.contrib import admin
from .models import Category, Product, StockMovement, Supplier


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'supplier', 'quantity', 'reorder_level')
    list_filter = ('category', 'supplier')
    search_fields = ('name', 'sku')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'created_by', 'created_at')
    list_filter = ('movement_type',)


admin.site.register(Category)
admin.site.register(Supplier)
