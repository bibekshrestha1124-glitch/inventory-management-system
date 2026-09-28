from django import forms

from .models import Category, Product, StockMovement, Supplier


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.Select):
                w.attrs['class'] = 'form-select'
            else:
                w.attrs['class'] = 'form-control'


class CategoryForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class SupplierForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}


class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'supplier', 'description',
                  'cost_price', 'selling_price', 'quantity', 'reorder_level']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Quantity on existing products may only change via Stock In / Stock Out.
            del self.fields['quantity']
        else:
            self.fields['quantity'].label = 'Opening stock'


class BaseStockForm(BootstrapMixin, forms.Form):
    movement_type = None
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    quantity = forms.IntegerField(min_value=1)
    note = forms.CharField(max_length=255, required=False)

    def clean(self):
        cleaned = super().clean()
        product, qty = cleaned.get('product'), cleaned.get('quantity')
        if self.movement_type == StockMovement.OUT and product and qty and qty > product.quantity:
            self.add_error('quantity', f'Only {product.quantity} unit(s) in stock.')
        return cleaned


class StockInForm(BaseStockForm):
    movement_type = StockMovement.IN
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), required=False)
    field_order = ['product', 'quantity', 'supplier', 'note']


class StockOutForm(BaseStockForm):
    movement_type = StockMovement.OUT
    note = forms.CharField(max_length=255, required=False, label='Reason / note')
