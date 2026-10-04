from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.inventory.models import StockBalance, StockMovement, Warehouse
from apps.inventory.services import InsufficientStockError, post_movement
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Supplier
from apps.purchasing.services import receive_order, submit_order
from apps.users.models import User


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email="admin@example.com", password="UniquePass123!")
        self.staff = User.objects.create_user(
            email="staff@example.com", password="UniquePass123!", role=User.Roles.STAFF
        )
        self.viewer = User.objects.create_user(email="viewer@example.com", password="UniquePass123!")
        self.main = Warehouse.objects.create(code="WH1", name="Main")
        self.east = Warehouse.objects.create(code="WH2", name="East")
        self.staff.assigned_warehouses.add(self.main)
        self.category = Category.objects.create(name="Parts")
        self.product = Product.objects.create(
            sku="P-1", name="Bolt", category=self.category, reorder_level=Decimal("5")
        )

    def _receipt(self, qty, user=None, warehouse=None):
        movement = StockMovement(
            movement_type=StockMovement.MovementType.RECEIPT,
            warehouse=warehouse or self.main,
            reference="R1",
        )
        return post_movement(
            user=user or self.admin,
            movement=movement,
            lines=[{"product": self.product, "quantity": Decimal(qty), "unit_cost": Decimal("1.00")}],
        )

    def test_receipt_increases_balance(self):
        self._receipt("10")
        balance = StockBalance.objects.get(product=self.product, warehouse=self.main)
        self.assertEqual(balance.quantity, Decimal("10.000"))

    def test_issue_cannot_exceed_stock(self):
        self._receipt("2")
        movement = StockMovement(
            movement_type=StockMovement.MovementType.ISSUE,
            warehouse=self.main,
        )
        with self.assertRaises(InsufficientStockError):
            post_movement(
                user=self.admin,
                movement=movement,
                lines=[{"product": self.product, "quantity": Decimal("5"), "unit_cost": None}],
            )

    def test_transfer_is_atomic(self):
        self._receipt("10")
        movement = StockMovement(
            movement_type=StockMovement.MovementType.TRANSFER,
            warehouse=self.main,
            destination_warehouse=self.east,
        )
        post_movement(
            user=self.admin,
            movement=movement,
            lines=[{"product": self.product, "quantity": Decimal("4"), "unit_cost": None}],
        )
        self.assertEqual(
            StockBalance.objects.get(product=self.product, warehouse=self.main).quantity,
            Decimal("6.000"),
        )
        self.assertEqual(
            StockBalance.objects.get(product=self.product, warehouse=self.east).quantity,
            Decimal("4.000"),
        )

    def test_staff_cannot_use_unassigned_warehouse(self):
        movement = StockMovement(
            movement_type=StockMovement.MovementType.RECEIPT,
            warehouse=self.east,
        )
        from apps.inventory.services import StockError

        with self.assertRaises(StockError):
            post_movement(
                user=self.staff,
                movement=movement,
                lines=[{"product": self.product, "quantity": Decimal("1"), "unit_cost": None}],
            )


class PurchaseOrderTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email="admin@example.com", password="UniquePass123!")
        self.main = Warehouse.objects.create(code="WH1", name="Main")
        self.category = Category.objects.create(name="Parts")
        self.product = Product.objects.create(sku="P-1", name="Bolt", category=self.category)
        self.supplier = Supplier.objects.create(code="S1", name="Acme")
        self.po = PurchaseOrder.objects.create(
            number="PO-TEST-1",
            supplier=self.supplier,
            warehouse=self.main,
            created_by=self.admin,
        )
        self.line = PurchaseOrderLine.objects.create(
            purchase_order=self.po,
            product=self.product,
            quantity_ordered=Decimal("10"),
            unit_cost=Decimal("2.00"),
        )

    def test_receive_updates_stock_and_status(self):
        submit_order(self.po)
        receive_order(
            user=self.admin,
            po=self.po,
            receipts=[{"line": self.line, "quantity": Decimal("4")}],
        )
        self.po.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.po.status, PurchaseOrder.Status.PARTIAL)
        self.assertEqual(self.line.quantity_received, Decimal("4"))
        self.assertEqual(
            StockBalance.objects.get(product=self.product, warehouse=self.main).quantity,
            Decimal("4.000"),
        )


class InventoryAPIPermissionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email="admin@example.com", password="UniquePass123!")
        self.viewer = User.objects.create_user(email="viewer@example.com", password="UniquePass123!")
        self.category = Category.objects.create(name="Parts")
        self.warehouse = Warehouse.objects.create(code="WH1", name="Main")

    def test_viewer_cannot_create_product(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.post(
            "/api/products/",
            {
                "sku": "X-1",
                "name": "Widget",
                "category": self.category.pk,
                "unit": "pcs",
                "reorder_level": "0",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_product_and_list_is_paginated(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/products/",
            {
                "sku": "x-1",
                "name": "Widget",
                "category": self.category.pk,
                "unit": "pcs",
                "reorder_level": "0",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["sku"], "X-1")
        listing = self.client.get("/api/products/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertIn("results", listing.data)
