from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Warehouse(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class StockBalance(models.Model):
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="balances",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="balances",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "warehouse")
        indexes = [models.Index(fields=["warehouse", "product"])]

    def __str__(self) -> str:
        return f"{self.product.sku} @ {self.warehouse.code}: {self.quantity}"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        RECEIPT = "receipt", "Receipt"
        ISSUE = "issue", "Issue"
        TRANSFER = "transfer", "Transfer"

    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="movements",
        help_text="Source warehouse for transfers; target warehouse otherwise.",
    )
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        null=True,
        blank=True,
    )
    reference = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    purchase_order = models.ForeignKey(
        "purchasing.PurchaseOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    posted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-posted_at"]
        indexes = [
            models.Index(fields=["movement_type", "posted_at"]),
            models.Index(fields=["warehouse"]),
        ]

    def clean(self):
        if self.movement_type == self.MovementType.TRANSFER:
            if not self.destination_warehouse:
                raise ValidationError("Transfers require a destination warehouse.")
            if self.destination_warehouse_id == self.warehouse_id:
                raise ValidationError("Source and destination warehouses must differ.")
        elif self.destination_warehouse_id:
            raise ValidationError("Only transfers may set a destination warehouse.")

    def __str__(self) -> str:
        return f"{self.get_movement_type_display()} #{self.pk}"


class StockMovementLine(models.Model):
    movement = models.ForeignKey(
        StockMovement,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="movement_lines",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("movement", "product")

    def clean(self):
        if self.quantity is None or self.quantity <= 0:
            raise ValidationError("Line quantity must be greater than zero.")
        if self.product_id and not self.product.is_active:
            raise ValidationError("Inactive products cannot be used on new movements.")

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity}"
