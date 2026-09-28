# Inventory Management System (Django)

A complete inventory management web app built with Django, Bootstrap 5 and SQLite.

## Features
- **Authentication**: register, login, logout (all pages are login-protected)
- **Product CRUD** with SKU, category, supplier, cost/selling price, reorder level
- **Category CRUD** and **Supplier management** (contact details, product counts)
- **Stock In** (goods received, optionally linked to a supplier) and **Stock Out** (sales, usage, write-offs)
  - Stock-out is blocked if it would make stock negative
  - Updates run in a database transaction with row locking
  - Every change is logged in a **movement history** (who, when, how many, note)
- **Low-stock products** page (quantity <= reorder level) with one-click restock
- **Search & filter**: products (text, category, supplier, stock status), movements (text, type), categories, suppliers
- **Pagination** on long lists
- **Dashboard**: totals, units in stock, stock value, low/out-of-stock counts, recent movements, products per category

## Models
`Category`, `Supplier`, `Product`, `StockMovement`

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # optional: demo data + user admin / admin12345
python manage.py runserver
```
Open http://127.0.0.1:8000/ . Django admin is at `/admin/`.

Create your own admin with `python manage.py createsuperuser`.

## Run tests
```bash
python manage.py test
```

## Project structure
```
inventory_project/   settings, root urls
inventory/           models, forms, views, urls, admin, tests
  templates/         base, dashboard, product/category/supplier/stock pages
  management/commands/seed_demo.py
```

## Design notes
- Product quantity is changed **only** through Stock In / Stock Out (the product edit form does not expose it), so the history always matches the current stock.
- Opening stock entered when creating a product is recorded as a Stock In movement.
- Deleting a category/supplier keeps its products (the link is set to empty).
