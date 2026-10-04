from django.contrib import admin

from apps.inventory.models import StockBalance, StockMovement, StockMovementLine, Warehouse


class StockMovementLineInline(admin.TabularInline):
    model = StockMovementLine
    extra = 0
    autocomplete_fields = ["product"]
    readonly_fields = ("product", "quantity", "unit_cost")
    can_delete = False


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "updated_at")
    list_filter = ("warehouse",)
    search_fields = ("product__sku", "product__name", "warehouse__code")
    autocomplete_fields = ["product", "warehouse"]
    readonly_fields = ("product", "warehouse", "quantity", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "movement_type", "warehouse", "destination_warehouse", "created_by", "posted_at")
    list_filter = ("movement_type", "warehouse")
    search_fields = ("reference", "notes")
    autocomplete_fields = ["warehouse", "destination_warehouse", "created_by", "purchase_order"]
    inlines = [StockMovementLineInline]
    readonly_fields = (
        "movement_type",
        "warehouse",
        "destination_warehouse",
        "reference",
        "notes",
        "purchase_order",
        "created_by",
        "posted_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
