from django import forms
from django.forms import inlineformset_factory

from apps.catalog.models import Product
from apps.core.forms import apply_bootstrap
from apps.inventory.selectors import warehouse_scope
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ("code", "name", "email", "phone", "address", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ("supplier", "warehouse", "notes")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)
        self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True)
        if user:
            self.fields["warehouse"].queryset = warehouse_scope(user).filter(is_active=True)


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ("product", "quantity_ordered", "unit_cost")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)
        self.fields["product"].queryset = Product.objects.filter(is_active=True)


POLineFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderLine,
    form=PurchaseOrderLineForm,
    extra=2,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class ReceiveForm(forms.Form):
    def __init__(self, *args, purchase_order: PurchaseOrder, **kwargs):
        super().__init__(*args, **kwargs)
        for line in purchase_order.lines.select_related("product"):
            remaining = line.remaining()
            self.fields[f"qty_{line.pk}"] = forms.DecimalField(
                required=False,
                min_value=0,
                max_value=remaining,
                decimal_places=3,
                max_digits=14,
                initial=remaining,
                label=f"{line.product.sku} remaining {remaining}",
            )
            apply_bootstrap(self)
