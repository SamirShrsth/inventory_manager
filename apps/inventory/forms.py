from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from apps.catalog.models import Product
from apps.core.forms import apply_bootstrap
from apps.inventory.models import StockMovement, StockMovementLine, Warehouse
from apps.inventory.selectors import warehouse_scope


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ("code", "name", "address", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = (
            "movement_type",
            "warehouse",
            "destination_warehouse",
            "reference",
            "notes",
        )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)
        qs = warehouse_scope(user) if user else Warehouse.objects.filter(is_active=True)
        qs = qs.filter(is_active=True)
        self.fields["warehouse"].queryset = qs
        self.fields["destination_warehouse"].queryset = qs
        self.fields["destination_warehouse"].required = False

    def clean(self):
        cleaned = super().clean()
        movement_type = cleaned.get("movement_type")
        dest = cleaned.get("destination_warehouse")
        warehouse = cleaned.get("warehouse")
        if movement_type == StockMovement.MovementType.TRANSFER:
            if not dest:
                self.add_error("destination_warehouse", "Required for transfers.")
            elif dest == warehouse:
                self.add_error("destination_warehouse", "Must differ from the source warehouse.")
        elif dest:
            self.add_error("destination_warehouse", "Only used for transfers.")
        return cleaned


class StockMovementLineForm(forms.ModelForm):
    class Meta:
        model = StockMovementLine
        fields = ("product", "quantity", "unit_cost")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)
        self.fields["product"].queryset = Product.objects.filter(is_active=True)
        self.fields["unit_cost"].required = False


MovementLineFormSet = inlineformset_factory(
    StockMovement,
    StockMovementLine,
    form=StockMovementLineForm,
    extra=2,
    min_num=1,
    validate_min=True,
    can_delete=True,
)
