from decimal import Decimal

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Product
from apps.inventory.models import StockBalance, StockMovement, StockMovementLine, Warehouse
from apps.inventory.selectors import warehouse_scope
from apps.inventory.services import StockError, post_movement
from apps.users.permissions import IsAdminRole, IsAuthenticatedReadOnlyOrStaff, IsStaffOrAdmin


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ("id", "code", "name", "address", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class StockBalanceSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    reorder_level = serializers.DecimalField(
        source="product.reorder_level", max_digits=14, decimal_places=3, read_only=True
    )

    class Meta:
        model = StockBalance
        fields = (
            "id",
            "product",
            "product_sku",
            "product_name",
            "warehouse",
            "warehouse_code",
            "quantity",
            "reorder_level",
            "updated_at",
        )
        read_only_fields = fields


class StockMovementLineSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = StockMovementLine
        fields = ("id", "product", "product_sku", "quantity", "unit_cost")
        read_only_fields = ("id", "product_sku")


class StockMovementSerializer(serializers.ModelSerializer):
    lines = StockMovementLineSerializer(many=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "movement_type",
            "warehouse",
            "destination_warehouse",
            "reference",
            "notes",
            "purchase_order",
            "created_by",
            "created_by_email",
            "posted_at",
            "lines",
        )
        read_only_fields = ("id", "created_by", "created_by_email", "posted_at", "purchase_order")

    def validate(self, attrs):
        movement = StockMovement(**{k: v for k, v in attrs.items() if k != "lines"})
        movement.created_by = self.context["request"].user
        try:
            movement.full_clean()
        except Exception as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", str(exc)))
        return attrs

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        user = self.context["request"].user
        movement = StockMovement(**validated_data)
        posted = post_movement(user=user, movement=movement, lines=lines)
        return posted


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrStaff]
    search_fields = ["code", "name", "address"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "code"]

    def get_queryset(self):
        return warehouse_scope(self.request.user)

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAdminRole()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class StockBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockBalanceSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrStaff]
    search_fields = ["product__sku", "product__name", "warehouse__code"]
    filterset_fields = ["warehouse", "product", "product__category"]
    ordering_fields = ["quantity", "updated_at", "product__name"]

    def get_queryset(self):
        qs = (
            StockBalance.objects.filter(warehouse__in=warehouse_scope(self.request.user))
            .select_related("product", "warehouse")
        )
        if self.request.query_params.get("low") == "1":
            from django.db.models import F

            qs = qs.filter(quantity__lte=F("product__reorder_level"))
        return qs


class StockMovementViewSet(viewsets.ModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrStaff]
    http_method_names = ["get", "post", "head", "options"]
    search_fields = ["reference", "notes", "lines__product__sku"]
    filterset_fields = ["movement_type", "warehouse"]
    ordering_fields = ["posted_at", "movement_type"]

    def get_queryset(self):
        return (
            StockMovement.objects.filter(warehouse__in=warehouse_scope(self.request.user))
            .select_related("warehouse", "destination_warehouse", "created_by")
            .prefetch_related("lines__product")
        )

    def get_permissions(self):
        if self.action in {"create", "transfer"}:
            return [IsStaffOrAdmin()]
        return super().get_permissions()

    @action(detail=False, methods=["post"], url_path="transfer")
    def transfer(self, request):
        data = request.data.copy()
        data["movement_type"] = StockMovement.MovementType.TRANSFER
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
