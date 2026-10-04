from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status

from apps.inventory.models import StockBalance, StockMovement, StockMovementLine


class StockError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST


class InsufficientStockError(StockError):
    status_code = status.HTTP_400_BAD_REQUEST


def _get_locked_balance(product, warehouse) -> StockBalance:
    balance, _ = StockBalance.objects.select_for_update().get_or_create(
        product=product,
        warehouse=warehouse,
        defaults={"quantity": Decimal("0")},
    )
    return balance


def apply_delta(product, warehouse, delta: Decimal) -> StockBalance:
    balance = _get_locked_balance(product, warehouse)
    new_qty = balance.quantity + delta
    if new_qty < 0:
        raise InsufficientStockError(
            f"Insufficient stock for {product.sku} in {warehouse.code}. "
            f"Available {balance.quantity}, requested change {delta}."
        )
    balance.quantity = new_qty
    balance.save(update_fields=["quantity", "updated_at"])
    return balance


def _line_delta(movement: StockMovement, quantity: Decimal) -> tuple[Decimal, Decimal | None]:
    """Return (source_delta, dest_delta). dest_delta is None unless transfer."""
    qty = quantity
    if movement.movement_type == StockMovement.MovementType.RECEIPT:
        return qty, None
    if movement.movement_type == StockMovement.MovementType.ISSUE:
        return -qty, None
    if movement.movement_type == StockMovement.MovementType.TRANSFER:
        return -qty, qty
    raise StockError("Unknown movement type.")


@transaction.atomic
def post_movement(*, user, movement: StockMovement, lines: list[dict]) -> StockMovement:
    if not lines:
        raise StockError("At least one line is required.")
    movement.created_by = user
    movement.full_clean()
    if not user.can_mutate_warehouse(movement.warehouse):
        raise StockError("You are not assigned to the source warehouse.")
    if movement.destination_warehouse and not user.can_mutate_warehouse(movement.destination_warehouse):
        raise StockError("You are not assigned to the destination warehouse.")
    movement.save()

    seen_products = set()
    for raw in lines:
        product = raw["product"]
        quantity = Decimal(str(raw["quantity"]))
        unit_cost = raw.get("unit_cost")
        if product.pk in seen_products:
            raise StockError(f"Duplicate product {product.sku} on the same movement.")
        seen_products.add(product.pk)
        if not product.is_active:
            raise StockError(f"Product {product.sku} is inactive.")
        if quantity <= 0:
            raise StockError("Line quantity must be greater than zero.")
        line = StockMovementLine(
            movement=movement,
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
        )
        line.full_clean()
        line.save()
        source_delta, dest_delta = _line_delta(movement, quantity)
        apply_delta(product, movement.warehouse, source_delta)
        if dest_delta is not None:
            apply_delta(product, movement.destination_warehouse, dest_delta)
    return movement
