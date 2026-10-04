from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.catalog.models import Product
from apps.inventory.models import StockBalance, StockMovement, Warehouse
from apps.inventory.selectors import warehouse_scope
from apps.purchasing.models import PurchaseOrder


@login_required
@require_GET
def dashboard(request):
    warehouses = warehouse_scope(request.user)
    balances = StockBalance.objects.filter(warehouse__in=warehouses).select_related(
        "product", "warehouse"
    )
    low_stock = (
        StockBalance.objects.filter(warehouse__in=warehouses)
        .select_related("product", "warehouse")
        .filter(quantity__lte=F("product__reorder_level"))
        .order_by("product__name", "warehouse__name")[:10]
    )
    recent_movements = (
        StockMovement.objects.filter(warehouse__in=warehouses)
        .select_related("warehouse", "destination_warehouse", "created_by")
        .prefetch_related("lines")
        .order_by("-posted_at")[:8]
    )
    pending_pos = PurchaseOrder.objects.filter(
        warehouse__in=warehouses,
        status__in=[
            PurchaseOrder.Status.SUBMITTED,
            PurchaseOrder.Status.PARTIAL,
        ],
    ).select_related("supplier", "warehouse")[:8]

    context = {
        "product_count": Product.objects.filter(is_active=True).count(),
        "warehouse_count": warehouses.filter(is_active=True).count(),
        "open_po_count": PurchaseOrder.objects.filter(
            warehouse__in=warehouses,
            status__in=[PurchaseOrder.Status.SUBMITTED, PurchaseOrder.Status.PARTIAL],
        ).count(),
        "movement_count": StockMovement.objects.filter(
            warehouse__in=warehouses,
            posted_at__date=timezone.now().date(),
        ).count(),
        "low_stock": low_stock,
        "recent_movements": recent_movements,
        "pending_pos": pending_pos,
        "balance_rows": balances.order_by("product__name", "warehouse__name")[:8],
    }
    return render(request, "core/dashboard.html", context)


def landing(request):
    if request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect("core:dashboard")
    return render(request, "core/landing.html")


def bad_request(request, exception=None):
    return render(request, "core/errors/400.html", status=400)


def permission_denied(request, exception=None):
    return render(request, "core/errors/403.html", status=403)


def page_not_found(request, exception=None):
    return render(request, "core/errors/404.html", status=404)


def server_error(request):
    return render(request, "core/errors/500.html", status=500)
