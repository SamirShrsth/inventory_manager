from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Category, Product, ProductSupplier
from apps.inventory.models import StockMovement, Warehouse
from apps.inventory.services import post_movement
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Supplier
from apps.purchasing.services import generate_po_number, receive_order, submit_order
from apps.users.models import User


class Command(BaseCommand):
    help = "Load realistic demo users, catalog, warehouses, stock, and purchase orders."

    @transaction.atomic
    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            email="admin@example.com",
            defaults={"role": User.Roles.ADMIN, "is_staff": True, "is_superuser": True, "username": "admin@example.com"},
        )
        if not admin.password or not admin.has_usable_password() or not admin.check_password("AdminPass123!"):
            admin.set_password("AdminPass123!")
            admin.role = User.Roles.ADMIN
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
        admin.profile.full_name = "Avery Admin"
        admin.profile.job_title = "Operations director"
        admin.profile.save()

        staff, _ = User.objects.get_or_create(
            email="staff@example.com",
            defaults={"role": User.Roles.STAFF, "username": "staff@example.com"},
        )
        staff.role = User.Roles.STAFF
        staff.set_password("StaffPass123!")
        staff.save()
        staff.profile.full_name = "Sam Clerk"
        staff.profile.job_title = "Warehouse clerk"
        staff.profile.save()

        viewer, _ = User.objects.get_or_create(
            email="viewer@example.com",
            defaults={"role": User.Roles.VIEWER, "username": "viewer@example.com"},
        )
        viewer.role = User.Roles.VIEWER
        viewer.set_password("ViewerPass123!")
        viewer.save()
        viewer.profile.full_name = "Val Viewer"
        viewer.profile.job_title = "Analyst"
        viewer.profile.save()

        main, _ = Warehouse.objects.get_or_create(
            code="WH-MAIN",
            defaults={"name": "Main distribution center", "address": "100 Warehouse Rd, Springfield"},
        )
        east, _ = Warehouse.objects.get_or_create(
            code="WH-EAST",
            defaults={"name": "East overflow", "address": "22 Harbor Ave"},
        )
        west, _ = Warehouse.objects.get_or_create(
            code="WH-WEST",
            defaults={"name": "West regional warehouse", "address": "45 Industrial Way, Springfield"},
        )
        cold, _ = Warehouse.objects.get_or_create(
            code="WH-COLD",
            defaults={"name": "Cold storage annex", "address": "8 Market Road, Springfield"},
        )
        staff.assigned_warehouses.set([main, east])

        category_data = [
            ("Electronics", "Consumer electronics and accessories."),
            ("Office supplies", "Everyday office and stationery supplies."),
            ("Packing", "Shipping and warehouse packing materials."),
            ("Cleaning", "Cleaning products and janitorial supplies."),
            ("Safety equipment", "Personal protective and workplace safety equipment."),
            ("Furniture", "Office furniture and workspace equipment."),
            ("Beverages", "Drinks and refreshments for staff areas."),
            ("Hardware", "Tools, fasteners and maintenance hardware."),
        ]
        categories = {}
        for name, description in category_data:
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={"slug": name.lower().replace(" ", "-"), "description": description},
            )
            categories[name] = category

        electronics = categories["Electronics"]
        office = categories["Office supplies"]
        packing = categories["Packing"]

        supplier_data = [
            ("SUP-ACME", "Acme Wholesale", "orders@acme.example", "555-0100", "1 Supplier Park"),
            ("SUP-NOVA", "Nova Office Goods", "sales@nova.example", "555-0112", "14 Commerce Street"),
            ("SUP-GREEN", "GreenClean Distributors", "orders@greenclean.example", "555-0130", "28 Service Avenue"),
            ("SUP-SAFE", "SafeWork Supplies", "dispatch@safework.example", "555-0144", "7 Industry Lane"),
            ("SUP-HOME", "HomeBase Furnishings", "trade@homebase.example", "555-0158", "90 Market Road"),
        ]
        suppliers = {}
        for code, name, email, phone, address in supplier_data:
            supplier, _ = Supplier.objects.get_or_create(
                code=code,
                defaults={"name": name, "email": email, "phone": phone, "address": address},
            )
            suppliers[code] = supplier
        supplier = suppliers["SUP-ACME"]

        products = [
            ("SKU-NB-14", "14-inch notebook", electronics, Product.Unit.PCS, Decimal("5"), "SUP-ACME", Decimal("540.00")),
            ("SKU-MS-01", "Wireless mouse", electronics, Product.Unit.PCS, Decimal("20"), "SUP-ACME", Decimal("9.50")),
            ("SKU-KB-02", "Compact USB keyboard", electronics, Product.Unit.PCS, Decimal("15"), "SUP-ACME", Decimal("14.00")),
            ("SKU-HD-1T", "1TB external hard drive", electronics, Product.Unit.PCS, Decimal("8"), "SUP-ACME", Decimal("62.00")),
            ("SKU-A4-80", "A4 copy paper 80gsm", office, Product.Unit.BOX, Decimal("10"), "SUP-NOVA", Decimal("18.00")),
            ("SKU-PEN-BL", "Blue ballpoint pens", office, Product.Unit.BOX, Decimal("12"), "SUP-NOVA", Decimal("7.50")),
            ("SKU-NOT-A5", "A5 ruled notebooks", office, Product.Unit.BOX, Decimal("8"), "SUP-NOVA", Decimal("21.00")),
            ("SKU-ST-12", "Desk stapler", office, Product.Unit.PCS, Decimal("6"), "SUP-NOVA", Decimal("5.25")),
            ("SKU-TB-50", "Packing tape 50m", packing, Product.Unit.PCS, Decimal("15"), "SUP-ACME", Decimal("3.20")),
            ("SKU-BX-M", "Medium shipping cartons", packing, Product.Unit.PCS, Decimal("30"), "SUP-ACME", Decimal("1.80")),
            ("SKU-BUB-10", "Bubble wrap roll 10m", packing, Product.Unit.PCS, Decimal("10"), "SUP-ACME", Decimal("8.75")),
            ("SKU-CL-5L", "Multi-purpose cleaner 5L", categories["Cleaning"], Product.Unit.L, Decimal("6"), "SUP-GREEN", Decimal("11.50")),
            ("SKU-GLV-100", "Nitrile gloves", categories["Safety equipment"], Product.Unit.BOX, Decimal("12"), "SUP-SAFE", Decimal("16.00")),
            ("SKU-CHA-01", "Ergonomic task chair", categories["Furniture"], Product.Unit.PCS, Decimal("4"), "SUP-HOME", Decimal("125.00")),
            ("SKU-WTR-24", "Bottled water case", categories["Beverages"], Product.Unit.BOX, Decimal("10"), "SUP-ACME", Decimal("4.50")),
            ("SKU-TOOL-8", "Maintenance tool set", categories["Hardware"], Product.Unit.PCS, Decimal("3"), "SUP-SAFE", Decimal("48.00")),
        ]
        created_products = []
        for sku, name, category, unit, reorder, supplier_code, cost in products:
            product, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": category,
                    "unit": unit,
                    "reorder_level": reorder,
                    "description": f"Standard stock item: {name}",
                },
            )
            ProductSupplier.objects.get_or_create(
                product=product,
                supplier=suppliers[supplier_code],
                defaults={"last_cost": cost, "supplier_sku": f"{supplier_code}-{sku}"},
            )
            created_products.append(product)

        if not StockMovement.objects.filter(reference="SEED-RECEIPT").exists():
            movement = StockMovement(
                movement_type=StockMovement.MovementType.RECEIPT,
                warehouse=main,
                reference="SEED-RECEIPT",
                notes="Opening balance from seed command",
            )
            lines = [
                {"product": created_products[0], "quantity": Decimal("12"), "unit_cost": Decimal("540.00")},
                {"product": created_products[1], "quantity": Decimal("80"), "unit_cost": Decimal("9.50")},
                {"product": created_products[2], "quantity": Decimal("25"), "unit_cost": Decimal("18.00")},
                {"product": created_products[3], "quantity": Decimal("8"), "unit_cost": Decimal("3.20")},
            ]
            post_movement(user=admin, movement=movement, lines=lines)

            transfer = StockMovement(
                movement_type=StockMovement.MovementType.TRANSFER,
                warehouse=main,
                destination_warehouse=east,
                reference="SEED-XFER",
                notes="Balance east warehouse",
            )
            post_movement(
                user=admin,
                movement=transfer,
                lines=[{"product": created_products[1], "quantity": Decimal("20"), "unit_cost": None}],
            )

        extra_movements = [
            (
                "SEED-RECEIPT-WEST",
                StockMovement.MovementType.RECEIPT,
                west,
                None,
                "Opening receipt for the west warehouse.",
                [
                    (created_products[2], Decimal("24"), Decimal("14.00")),
                    (created_products[4], Decimal("40"), Decimal("18.00")),
                    (created_products[8], Decimal("60"), Decimal("3.20")),
                    (created_products[12], Decimal("18"), Decimal("11.50")),
                ],
            ),
            (
                "SEED-RECEIPT-COLD",
                StockMovement.MovementType.RECEIPT,
                cold,
                None,
                "Opening receipt for temperature-sensitive supplies.",
                [(created_products[14], Decimal("36"), Decimal("4.50"))],
            ),
            (
                "SEED-ISSUE-MAIN",
                StockMovement.MovementType.ISSUE,
                main,
                None,
                "Weekly office consumption.",
                [(created_products[1], Decimal("8"), None), (created_products[0], Decimal("2"), None)],
            ),
            (
                "SEED-ISSUE-WEST",
                StockMovement.MovementType.ISSUE,
                west,
                None,
                "Packing team issue.",
                [(created_products[8], Decimal("12"), None), (created_products[2], Decimal("4"), None)],
            ),
            (
                "SEED-XFER-WEST-EAST",
                StockMovement.MovementType.TRANSFER,
                west,
                east,
                "Rebalancing stock for the east warehouse.",
                [(created_products[4], Decimal("10"), None), (created_products[8], Decimal("6"), None)],
            ),
        ]
        for reference, movement_type, warehouse, destination, notes, movement_lines in extra_movements:
            if StockMovement.objects.filter(reference=reference).exists():
                continue
            movement = StockMovement(
                movement_type=movement_type,
                warehouse=warehouse,
                destination_warehouse=destination,
                reference=reference,
                notes=notes,
            )
            post_movement(
                user=admin,
                movement=movement,
                lines=[
                    {"product": product, "quantity": quantity, "unit_cost": unit_cost}
                    for product, quantity, unit_cost in movement_lines
                ],
            )

        if not PurchaseOrder.objects.filter(notes="Seed submitted PO").exists():
            po = PurchaseOrder.objects.create(
                number=generate_po_number(),
                supplier=supplier,
                warehouse=main,
                created_by=staff,
                notes="Seed submitted PO",
            )
            PurchaseOrderLine.objects.create(
                purchase_order=po,
                product=created_products[3],
                quantity_ordered=Decimal("40"),
                unit_cost=Decimal("3.10"),
            )
            submit_order(po)
        else:
            submitted_po = PurchaseOrder.objects.get(notes="Seed submitted PO")
            if submitted_po.status == PurchaseOrder.Status.CANCELLED and not submitted_po.lines.filter(
                quantity_received__gt=0
            ).exists():
                submitted_po.status = PurchaseOrder.Status.SUBMITTED
                submitted_po.submitted_at = submitted_po.submitted_at or timezone.now()
                submitted_po.save(update_fields=["status", "submitted_at", "updated_at"])

        po_specs = [
            (
                "Seed draft PO",
                suppliers["SUP-NOVA"],
                east,
                [(created_products[5], Decimal("80"), Decimal("7.50"))],
                "draft",
            ),
            (
                "Seed cancelled PO",
                suppliers["SUP-GREEN"],
                west,
                [(created_products[11], Decimal("20"), Decimal("11.50"))],
                "cancelled",
            ),
            (
                "Seed partial PO",
                suppliers["SUP-SAFE"],
                main,
                [(created_products[12], Decimal("50"), Decimal("16.00"), Decimal("20"))],
                "partial",
            ),
            (
                "Seed received PO",
                suppliers["SUP-HOME"],
                west,
                [(created_products[13], Decimal("10"), Decimal("125.00"), Decimal("10"))],
                "received",
            ),
        ]
        for notes, po_supplier, warehouse, lines, target_status in po_specs:
            if PurchaseOrder.objects.filter(notes=notes).exists():
                continue
            po = PurchaseOrder.objects.create(
                number=generate_po_number(),
                supplier=po_supplier,
                warehouse=warehouse,
                created_by=admin,
                notes=notes,
            )
            for line in lines:
                product, quantity, unit_cost = line[:3]
                received = line[3] if len(line) > 3 else Decimal("0")
                PurchaseOrderLine.objects.create(
                    purchase_order=po,
                    product=product,
                    quantity_ordered=quantity,
                    quantity_received=Decimal("0"),
                    unit_cost=unit_cost,
                )
            if target_status != "draft":
                submit_order(po)
            if target_status == "cancelled":
                po.status = PurchaseOrder.Status.CANCELLED
                po.save(update_fields=["status", "updated_at"])
            elif target_status in {"partial", "received"}:
                receipt_lines = [
                    {"line": po.lines.get(product=product), "quantity": received}
                    for product, _, _, received in lines
                ]
                receive_order(user=admin, po=po, receipts=receipt_lines)

        self.stdout.write(self.style.SUCCESS("Sample data loaded."))
        self.stdout.write("Admin  admin@example.com / AdminPass123!")
        self.stdout.write("Staff  staff@example.com / StaffPass123!  (assigned to WH-MAIN)")
        self.stdout.write("Viewer viewer@example.com / ViewerPass123!")
