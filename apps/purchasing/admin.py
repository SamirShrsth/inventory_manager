from django.contrib import admin

from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Supplier


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0
    autocomplete_fields = ["product"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "email")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "supplier", "warehouse", "status", "created_by", "created_at")
    list_filter = ("status", "warehouse", "supplier")
    search_fields = ("number", "supplier__name")
    autocomplete_fields = ["supplier", "warehouse", "created_by"]
    inlines = [PurchaseOrderLineInline]
    readonly_fields = ("number", "status", "submitted_at", "created_at", "updated_at")
