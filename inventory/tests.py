from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, InsufficientStock, Product, StockMovement, Supplier, apply_movement


class BaseTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('tester', password='pass12345')
        self.client.login(username='tester', password='pass12345')
        self.cat = Category.objects.create(name='Electronics')
        self.sup = Supplier.objects.create(name='Acme')
        self.p = Product.objects.create(name='Mouse', sku='M1', category=self.cat, supplier=self.sup,
                                        cost_price=10, selling_price=15, quantity=20, reorder_level=5)


class StockLogicTests(BaseTest):
    def test_stock_in_increases_quantity(self):
        apply_movement(self.p, StockMovement.IN, 5, user=self.user)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 25)
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_stock_out_decreases_quantity(self):
        apply_movement(self.p, StockMovement.OUT, 8)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 12)

    def test_cannot_go_negative(self):
        with self.assertRaises(InsufficientStock):
            apply_movement(self.p, StockMovement.OUT, 21)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 20)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_low_stock_flag(self):
        apply_movement(self.p, StockMovement.OUT, 15)
        self.p.refresh_from_db()
        self.assertTrue(self.p.is_low_stock)


class ViewTests(BaseTest):
    def test_login_required(self):
        self.client.logout()
        r = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(r.status_code, 302)

    def test_dashboard_and_lists_load(self):
        for name in ['dashboard', 'product_list', 'category_list', 'supplier_list', 'movement_list',
                     'low_stock', 'stock_in', 'stock_out', 'product_create', 'category_create', 'supplier_create']:
            self.assertEqual(self.client.get(reverse(f'inventory:{name}')).status_code, 200, name)
        self.assertEqual(self.client.get(self.p.get_absolute_url()).status_code, 200)

    def test_product_create_records_opening_stock(self):
        r = self.client.post(reverse('inventory:product_create'), {
            'name': 'Pen', 'sku': 'P1', 'cost_price': '1', 'selling_price': '2', 'quantity': '30', 'reorder_level': '5'})
        self.assertEqual(r.status_code, 302)
        pen = Product.objects.get(sku='P1')
        self.assertEqual(pen.movements.get().quantity, 30)

    def test_product_edit_cannot_change_quantity(self):
        self.client.post(reverse('inventory:product_update', args=[self.p.pk]), {
            'name': 'Mouse2', 'sku': 'M1', 'cost_price': '10', 'selling_price': '15', 'reorder_level': '5', 'quantity': '999'})
        self.p.refresh_from_db()
        self.assertEqual(self.p.name, 'Mouse2')
        self.assertEqual(self.p.quantity, 20)

    def test_stock_out_view_blocks_oversell(self):
        r = self.client.post(reverse('inventory:stock_out'), {'product': self.p.pk, 'quantity': 50})
        self.assertEqual(r.status_code, 200)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 20)

    def test_stock_in_view(self):
        self.client.post(reverse('inventory:stock_in'), {'product': self.p.pk, 'quantity': 10, 'supplier': self.sup.pk})
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 30)

    def test_search_and_filters(self):
        Product.objects.create(name='Keyboard', sku='K1', cost_price=1, selling_price=2, quantity=0, reorder_level=5)
        url = reverse('inventory:product_list')
        self.assertContains(self.client.get(url, {'q': 'mou'}), 'Mouse')
        self.assertNotContains(self.client.get(url, {'q': 'mou'}), 'Keyboard')
        self.assertContains(self.client.get(url, {'status': 'out'}), 'Keyboard')
        self.assertNotContains(self.client.get(url, {'status': 'out'}), 'Mouse')
        self.assertEqual(self.client.get(url, {'category': 'abc'}).status_code, 200)

    def test_delete_category_keeps_products(self):
        self.client.post(reverse('inventory:category_delete', args=[self.cat.pk]))
        self.p.refresh_from_db()
        self.assertIsNone(self.p.category)

    def test_register(self):
        self.client.logout()
        r = self.client.post(reverse('inventory:register'), {'username': 'newuser', 'password1': 'Str0ngPass!234', 'password2': 'Str0ngPass!234'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='newuser').exists())
