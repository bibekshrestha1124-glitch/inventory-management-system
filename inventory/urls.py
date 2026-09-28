from django.urls import path
from . import views as v

app_name = 'inventory'

urlpatterns = [
    path('', v.dashboard, name='dashboard'),
    path('register/', v.register, name='register'),

    path('products/', v.ProductListView.as_view(), name='product_list'),
    path('products/add/', v.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', v.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', v.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', v.ProductDeleteView.as_view(), name='product_delete'),
    path('low-stock/', v.low_stock, name='low_stock'),

    path('categories/', v.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', v.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', v.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', v.CategoryDeleteView.as_view(), name='category_delete'),

    path('suppliers/', v.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/add/', v.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/edit/', v.SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/<int:pk>/delete/', v.SupplierDeleteView.as_view(), name='supplier_delete'),

    path('stock/in/', v.stock_move, {'kind': 'in'}, name='stock_in'),
    path('stock/out/', v.stock_move, {'kind': 'out'}, name='stock_out'),
    path('stock/history/', v.MovementListView.as_view(), name='movement_list'),
]
