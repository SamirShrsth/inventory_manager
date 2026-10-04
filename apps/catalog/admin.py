from django.contrib import admin

from apps.catalog.models import Category, Product, ProductSupplier


class ProductSupplierInline(admin.TabularInline):
    model = ProductSupplier
    extra = 0
    autocomplete_fields = ["supplier"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "unit", "reorder_level", "is_active")
    list_filter = ("category", "is_active", "unit")
    search_fields = ("sku", "name")
    autocomplete_fields = ["category"]
    inlines = [ProductSupplierInline]


@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ("product", "supplier", "supplier_sku", "last_cost")
    search_fields = ("product__sku", "supplier__name")
    autocomplete_fields = ["product", "supplier"]
