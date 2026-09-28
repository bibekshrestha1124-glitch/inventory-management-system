from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from inventory.models import Category, Product, StockMovement, Supplier, apply_movement


class Command(BaseCommand):
    help = 'Load demo data (categories, suppliers, products, movements) and a demo user.'

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
        if created:
            user.set_password('admin12345')
            user.save()
            self.stdout.write('Created user admin / admin12345')

        cats = {n: Category.objects.get_or_create(name=n)[0] for n in ['Electronics', 'Groceries', 'Stationery', 'Furniture']}
        sups = {n: Supplier.objects.get_or_create(name=n, defaults={'contact_person': c, 'phone': p, 'email': e})[0]
                for n, c, p, e in [('Himalayan Traders', 'Ram Sharma', '9800000001', 'ram@himalayan.example'),
                                   ('Kathmandu Supplies', 'Sita Karki', '9800000002', 'sita@ktm.example'),
                                   ('Pokhara Wholesale', 'Hari Thapa', '9800000003', 'hari@pokhara.example')]}
        data = [
            ('Wireless Mouse', 'EL-001', 'Electronics', 'Himalayan Traders', 700, 1000, 25, 10),
            ('USB-C Cable', 'EL-002', 'Electronics', 'Himalayan Traders', 150, 300, 5, 15),
            ('Bluetooth Speaker', 'EL-003', 'Electronics', 'Kathmandu Supplies', 2200, 3200, 0, 5),
            ('Basmati Rice 5kg', 'GR-001', 'Groceries', 'Pokhara Wholesale', 650, 800, 60, 20),
            ('Cooking Oil 1L', 'GR-002', 'Groceries', 'Pokhara Wholesale', 220, 280, 8, 15),
            ('A4 Paper Ream', 'ST-001', 'Stationery', 'Kathmandu Supplies', 450, 600, 40, 10),
            ('Ball Pen (Box of 50)', 'ST-002', 'Stationery', 'Kathmandu Supplies', 300, 450, 12, 10),
            ('Office Chair', 'FU-001', 'Furniture', 'Himalayan Traders', 4500, 6500, 4, 5),
        ]
        for name, sku, cat, sup, cost, price, qty, reorder in data:
            p, made = Product.objects.get_or_create(sku=sku, defaults=dict(
                name=name, category=cats[cat], supplier=sups[sup], cost_price=cost,
                selling_price=price, quantity=0, reorder_level=reorder))
            if made and qty:
                apply_movement(p, StockMovement.IN, qty, user=user, supplier=sups[sup], note='Opening stock')
        self.stdout.write(self.style.SUCCESS('Demo data loaded.'))
