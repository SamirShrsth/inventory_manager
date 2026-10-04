from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Supplier(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PARTIAL = "partial", "Partially received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=32, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["number"]), models.Index(fields=["status"])]

    def __str__(self) -> str:
        return self.number

    def refresh_receive_status(self) -> None:
        lines = list(self.lines.all())
        if not lines:
            return
        received = all(line.quantity_received >= line.quantity_ordered for line in lines)
        any_received = any(line.quantity_received > 0 for line in lines)
        if received:
            self.status = self.Status.RECEIVED
        elif any_received:
            self.status = self.Status.PARTIAL
        self.save(update_fields=["status", "updated_at"])


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
    )
    quantity_ordered = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_received = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = ("purchase_order", "product")

    def clean(self):
        if self.quantity_ordered is None or self.quantity_ordered <= 0:
            raise ValidationError("Ordered quantity must be greater than zero.")
        if self.quantity_received < 0:
            raise ValidationError("Received quantity cannot be negative.")
        if self.quantity_received > self.quantity_ordered:
            raise ValidationError("Cannot receive more than ordered.")

    def remaining(self) -> Decimal:
        return self.quantity_ordered - self.quantity_received

    def __str__(self) -> str:
        return f"{self.purchase_order.number} {self.product.sku}"
