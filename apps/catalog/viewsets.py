from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Category, Product, ProductSupplier
from apps.users.permissions import IsAdminOrReadOnlyStaffWrite, IsAuthenticatedReadOnlyOrStaff


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        qs = Category.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value


class ProductSupplierSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = ProductSupplier
        fields = ("id", "supplier", "supplier_name", "supplier_sku", "last_cost")


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    supplier_links = ProductSupplierSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "sku",
            "name",
            "category",
            "category_name",
            "unit",
            "description",
            "reorder_level",
            "is_active",
            "supplier_links",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "category_name", "supplier_links")

    def validate_sku(self, value):
        qs = Product.objects.filter(sku__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("SKU must be unique.")
        return value.upper()


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnlyStaffWrite]
    search_fields = ["name", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]

    def perform_destroy(self, instance):
        if instance.products.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
        else:
            instance.delete()


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").prefetch_related("supplier_links__supplier")
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrStaff]
    search_fields = ["sku", "name", "description"]
    filterset_fields = ["category", "is_active", "unit"]
    ordering_fields = ["name", "sku", "created_at"]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["get"])
    def stock(self, request, pk=None):
        from apps.inventory.models import StockBalance
        from apps.inventory.serializers import StockBalanceSerializer
        from apps.inventory.selectors import warehouse_scope

        product = self.get_object()
        qs = StockBalance.objects.filter(
            product=product,
            warehouse__in=warehouse_scope(request.user),
        ).select_related("warehouse", "product")
        page = self.paginate_queryset(qs)
        serializer = StockBalanceSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
