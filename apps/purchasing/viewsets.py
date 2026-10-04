from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.inventory.selectors import warehouse_scope
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Supplier
from apps.purchasing.services import (
    PurchasingError,
    cancel_order,
    generate_po_number,
    receive_order,
    submit_order,
)
from apps.users.permissions import IsAdminOrReadOnlyStaffWrite, IsAuthenticatedReadOnlyOrStaff, IsStaffOrAdmin


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = (
            "id",
            "code",
            "name",
            "email",
            "phone",
            "address",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    remaining = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = (
            "id",
            "product",
            "product_sku",
            "quantity_ordered",
            "quantity_received",
            "remaining",
            "unit_cost",
        )
        read_only_fields = ("id", "quantity_received", "remaining", "product_sku")


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = (
            "id",
            "number",
            "supplier",
            "supplier_name",
            "warehouse",
            "warehouse_code",
            "status",
            "notes",
            "created_by",
            "submitted_at",
            "created_at",
            "updated_at",
            "lines",
        )
        read_only_fields = (
            "id",
            "number",
            "status",
            "created_by",
            "submitted_at",
            "created_at",
            "updated_at",
            "supplier_name",
            "warehouse_code",
        )

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        user = self.context["request"].user
        warehouse = validated_data["warehouse"]
        if not user.can_mutate_warehouse(warehouse):
            raise serializers.ValidationError({"warehouse": "You are not assigned to this warehouse."})
        po = PurchaseOrder.objects.create(
            number=generate_po_number(),
            created_by=user,
            **validated_data,
        )
        for line in lines:
            PurchaseOrderLine.objects.create(purchase_order=po, **line)
        return po

    def update(self, instance, validated_data):
        if instance.status != PurchaseOrder.Status.DRAFT:
            raise serializers.ValidationError("Only draft purchase orders can be edited.")
        lines = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            for line in lines:
                PurchaseOrderLine.objects.create(purchase_order=instance, **line)
        return instance


class ReceiveSerializer(serializers.Serializer):
    lines = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_lines(self, value):
        cleaned = []
        for item in value:
            if "id" not in item or "quantity" not in item:
                raise serializers.ValidationError("Each line needs id and quantity.")
            cleaned.append(item)
        return cleaned


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminOrReadOnlyStaffWrite]
    search_fields = ["code", "name", "email"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "code"]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrStaff]
    http_method_names = ["get", "post", "patch", "head", "options"]
    search_fields = ["number", "supplier__name", "notes"]
    filterset_fields = ["status", "supplier", "warehouse"]
    ordering_fields = ["created_at", "number", "status"]

    def get_queryset(self):
        return (
            PurchaseOrder.objects.filter(warehouse__in=warehouse_scope(self.request.user))
            .select_related("supplier", "warehouse", "created_by")
            .prefetch_related("lines__product")
        )

    def get_permissions(self):
        if self.action in {"create", "partial_update", "submit", "receive", "cancel"}:
            return [IsStaffOrAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        po = self.get_object()
        submit_order(po)
        return Response(self.get_serializer(po).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        po = self.get_object()
        cancel_order(po)
        return Response(self.get_serializer(po).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        po = self.get_object()
        serializer = ReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipts = []
        for item in serializer.validated_data["lines"]:
            line = po.lines.filter(pk=item["id"]).first()
            if not line:
                raise PurchasingError(f"Unknown line id {item['id']}.")
            receipts.append({"line": line, "quantity": item["quantity"]})
        movement = receive_order(user=request.user, po=po, receipts=receipts)
        po.refresh_from_db()
        data = self.get_serializer(po).data
        data["movement_id"] = movement.pk
        return Response(data, status=status.HTTP_200_OK)
