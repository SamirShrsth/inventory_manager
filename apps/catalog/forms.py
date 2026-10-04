from django import forms

from apps.catalog.models import Category, Product
from apps.core.forms import apply_bootstrap


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)
        self.fields["slug"].required = False


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "sku",
            "name",
            "category",
            "unit",
            "description",
            "reorder_level",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
