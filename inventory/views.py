from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import CategoryForm, ProductForm, StockInForm, StockOutForm, SupplierForm
from .models import (Category, InsufficientStock, Product, StockMovement,
                     Supplier, apply_movement)


def register(request):
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Account created. Welcome!')
        return redirect('inventory:dashboard')
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard(request):
    products = Product.objects.all()
    value = products.aggregate(v=Sum(ExpressionWrapper(
        F('quantity') * F('cost_price'), output_field=DecimalField(max_digits=14, decimal_places=2))))['v'] or 0
    low = products.filter(quantity__lte=F('reorder_level'))
    categories = Category.objects.annotate(n=Count('products'), units=Sum('products__quantity'))
    max_n = max([c.n for c in categories], default=0) or 1
    context = {
        'total_products': products.count(),
        'total_categories': Category.objects.count(),
        'total_suppliers': Supplier.objects.count(),
        'total_units': products.aggregate(u=Sum('quantity'))['u'] or 0,
        'stock_value': value,
        'low_count': low.count(),
        'out_count': products.filter(quantity=0).count(),
        'low_products': low.select_related('category').order_by('quantity')[:6],
        'recent_movements': StockMovement.objects.select_related('product', 'created_by')[:8],
        'categories': categories,
        'max_n': max_n,
    }
    return render(request, 'inventory/dashboard.html', context)


class QueryStringMixin:
    """Keeps filters when moving between pages."""
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.copy()
        q.pop('page', None)
        ctx['querystring'] = q.urlencode()
        return ctx


# ---------- Products ----------
class ProductListView(LoginRequiredMixin, QueryStringMixin, ListView):
    model = Product
    paginate_by = 10
    template_name = 'inventory/product_list.html'

    def get_queryset(self):
        qs = Product.objects.select_related('category', 'supplier')
        g = self.request.GET
        q = g.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
        if g.get('category', '').isdigit():
            qs = qs.filter(category_id=g['category'])
        if g.get('supplier', '').isdigit():
            qs = qs.filter(supplier_id=g['supplier'])
        status = g.get('status')
        if status == 'out':
            qs = qs.filter(quantity=0)
        elif status == 'low':
            qs = qs.filter(quantity__gt=0, quantity__lte=F('reorder_level'))
        elif status == 'in':
            qs = qs.filter(quantity__gt=F('reorder_level'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(categories=Category.objects.all(), suppliers=Supplier.objects.all(),
                   q=self.request.GET.get('q', ''),
                   sel_category=self.request.GET.get('category', ''),
                   sel_supplier=self.request.GET.get('supplier', ''),
                   sel_status=self.request.GET.get('status', ''))
        return ctx


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['movements'] = self.object.movements.select_related('supplier', 'created_by')[:20]
        return ctx


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/form.html'
    extra_context = {'title': 'Add product', 'cancel_url': reverse_lazy('inventory:product_list')}

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.quantity:
            StockMovement.objects.create(product=self.object, movement_type=StockMovement.IN,
                                         quantity=self.object.quantity, note='Opening stock',
                                         supplier=self.object.supplier, created_by=self.request.user)
        messages.success(self.request, 'Product created.')
        return response


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(title=f'Edit {self.object.name}', cancel_url=self.object.get_absolute_url())
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Product updated.')
        return super().form_valid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cancel_url'] = self.object.get_absolute_url()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Product deleted.')
        return super().form_valid(form)


@login_required
def low_stock(request):
    products = Product.objects.filter(quantity__lte=F('reorder_level')).select_related('category', 'supplier').order_by('quantity')
    return render(request, 'inventory/low_stock.html', {'products': products})


# ---------- Categories & Suppliers (shared generic behaviour) ----------
class SimpleCRUDMixin(LoginRequiredMixin):
    label = ''
    list_url = ''

    def form_valid(self, form):
        messages.success(self.request, f'{self.label} saved.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(self.list_url)


class CategoryListView(LoginRequiredMixin, ListView):
    template_name = 'inventory/category_list.html'

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        qs = Category.objects.annotate(n=Count('products')).order_by('name')
        return qs.filter(name__icontains=q) if q else qs


class CategoryCreateView(SimpleCRUDMixin, CreateView):
    model, form_class, template_name = Category, CategoryForm, 'inventory/form.html'
    label, list_url = 'Category', 'inventory:category_list'
    extra_context = {'title': 'Add category', 'cancel_url': reverse_lazy('inventory:category_list')}


class CategoryUpdateView(SimpleCRUDMixin, UpdateView):
    model, form_class, template_name = Category, CategoryForm, 'inventory/form.html'
    label, list_url = 'Category', 'inventory:category_list'
    extra_context = {'title': 'Edit category', 'cancel_url': reverse_lazy('inventory:category_list')}


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')
    extra_context = {'cancel_url': reverse_lazy('inventory:category_list'),
                     'warning': 'Products in this category will be kept but left uncategorised.'}


class SupplierListView(LoginRequiredMixin, ListView):
    template_name = 'inventory/supplier_list.html'
    paginate_by = 10

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        qs = Supplier.objects.annotate(n=Count('products')).order_by('name')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(contact_person__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
        return qs


class SupplierCreateView(SimpleCRUDMixin, CreateView):
    model, form_class, template_name = Supplier, SupplierForm, 'inventory/form.html'
    label, list_url = 'Supplier', 'inventory:supplier_list'
    extra_context = {'title': 'Add supplier', 'cancel_url': reverse_lazy('inventory:supplier_list')}


class SupplierUpdateView(SimpleCRUDMixin, UpdateView):
    model, form_class, template_name = Supplier, SupplierForm, 'inventory/form.html'
    label, list_url = 'Supplier', 'inventory:supplier_list'
    extra_context = {'title': 'Edit supplier', 'cancel_url': reverse_lazy('inventory:supplier_list')}


class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'inventory/confirm_delete.html'
    success_url = reverse_lazy('inventory:supplier_list')
    extra_context = {'cancel_url': reverse_lazy('inventory:supplier_list'),
                     'warning': 'Products from this supplier will be kept without a supplier.'}


# ---------- Stock in / out ----------
@login_required
def stock_move(request, kind):
    is_in = kind == 'in'
    Form = StockInForm if is_in else StockOutForm
    initial = {}
    if request.GET.get('product', '').isdigit():
        initial['product'] = request.GET['product']
    form = Form(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        try:
            m = apply_movement(d['product'], form.movement_type, d['quantity'], user=request.user,
                               supplier=d.get('supplier'), note=d['note'])
        except InsufficientStock as e:
            form.add_error('quantity', str(e))
        else:
            verb = 'added to' if is_in else 'removed from'
            messages.success(request, f'{m.quantity} unit(s) {verb} {m.product.name}. New stock: {m.product.quantity}.')
            return redirect('inventory:movement_list')
    return render(request, 'inventory/stock_form.html', {'form': form, 'is_in': is_in})


class MovementListView(LoginRequiredMixin, QueryStringMixin, ListView):
    paginate_by = 15
    template_name = 'inventory/movement_list.html'

    def get_queryset(self):
        qs = StockMovement.objects.select_related('product', 'supplier', 'created_by')
        g = self.request.GET
        q = g.get('q', '').strip()
        if q:
            qs = qs.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q) | Q(note__icontains=q))
        if g.get('type') in (StockMovement.IN, StockMovement.OUT):
            qs = qs.filter(movement_type=g['type'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(q=self.request.GET.get('q', ''), sel_type=self.request.GET.get('type', ''))
        return ctx
