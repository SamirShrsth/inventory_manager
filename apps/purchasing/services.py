from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status

from apps.inventory.models import StockMovement
from apps.inventory.services import post_movement
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine


class PurchasingError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST


class ConflictError(PurchasingError):
    status_code = status.HTTP_409_CONFLICT


def generate_po_number() -> str:
    today = timezone.now().strftime("%Y%m%d")
    prefix = f"PO-{today}-"
    last = (
        PurchaseOrder.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = 1
    if last:
        seq = int(last.split("-")[-1]) + 1
    return f"{prefix}{seq:04d}"


def submit_order(po: PurchaseOrder) -> PurchaseOrder:
    if po.status != PurchaseOrder.Status.DRAFT:
        raise PurchasingError("Only draft purchase orders can be submitted.")
    if not po.lines.exists():
        raise PurchasingError("Add at least one line before submitting.")
    po.status = PurchaseOrder.Status.SUBMITTED
    po.submitted_at = timezone.now()
    po.save(update_fields=["status", "submitted_at", "updated_at"])
    return po


def cancel_order(po: PurchaseOrder) -> PurchaseOrder:
    if po.status in {PurchaseOrder.Status.RECEIVED, PurchaseOrder.Status.CANCELLED}:
        raise PurchasingError("This purchase order cannot be cancelled.")
    if po.lines.filter(quantity_received__gt=0).exists():
        raise PurchasingError("Cannot cancel a purchase order that already has receipts.")
    po.status = PurchaseOrder.Status.CANCELLED
    po.save(update_fields=["status", "updated_at"])
    return po


@transaction.atomic
def receive_order(*, user, po: PurchaseOrder, receipts: list[dict]) -> StockMovement:
    po = PurchaseOrder.objects.select_for_update().get(pk=po.pk)
    if po.status not in {PurchaseOrder.Status.SUBMITTED, PurchaseOrder.Status.PARTIAL}:
        raise PurchasingError("Only submitted or partially received orders can be received.")
    if not user.can_mutate_warehouse(po.warehouse):
        raise PurchasingError("You are not assigned to this warehouse.")
    if not receipts:
        raise PurchasingError("Provide at least one receipt line.")

    movement_lines = []
    for item in receipts:
        line: PurchaseOrderLine = item["line"]
        qty = Decimal(str(item["quantity"]))
        if line.purchase_order_id != po.pk:
            raise PurchasingError("Line does not belong to this purchase order.")
        if qty <= 0:
            raise PurchasingError("Receipt quantity must be greater than zero.")
        remaining = line.remaining()
        if qty > remaining:
            raise PurchasingError(
                f"Cannot receive {qty} of {line.product.sku}; remaining {remaining}."
            )
        line.quantity_received += qty
        line.save(update_fields=["quantity_received"])
        movement_lines.append(
            {
                "product": line.product,
                "quantity": qty,
                "unit_cost": line.unit_cost,
            }
        )

    movement = StockMovement(
        movement_type=StockMovement.MovementType.RECEIPT,
        warehouse=po.warehouse,
        reference=po.number,
        notes=f"Receipt against {po.number}",
        purchase_order=po,
    )
    posted = post_movement(user=user, movement=movement, lines=movement_lines)
    po.refresh_receive_status()
    return posted
