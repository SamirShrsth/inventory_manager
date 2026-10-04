from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.catalog.models import Category, Product
from apps.core.mixins import AdminRequiredMixin, StaffRequiredMixin
from apps.inventory.forms import MovementLineFormSet, StockMovementForm, WarehouseForm
from apps.inventory.models import StockBalance, StockMovement, Warehouse
from apps.inventory.selectors import warehouse_scope
from apps.inventory.services import StockError, post_movement


class WarehouseListView(LoginRequiredMixin, ListView):
    model = Warehouse
    template_name = "inventory/warehouse_list.html"
    paginate_by = 20


class WarehouseCreateView(AdminRequiredMixin, CreateView):
    form_class = WarehouseForm
    template_name = "inventory/warehouse_form.html"
    success_url = reverse_lazy("inventory:warehouse-list")

    def form_valid(self, form):
        messages.success(self.request, "Warehouse created.")
        return super().form_valid(form)


class WarehouseUpdateView(AdminRequiredMixin, UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = "inventory/warehouse_form.html"
    success_url = reverse_lazy("inventory:warehouse-list")

    def form_valid(self, form):
        messages.success(self.request, "Warehouse updated.")
        return super().form_valid(form)


class WarehouseDetailView(LoginRequiredMixin, DetailView):
    model = Warehouse
    template_name = "inventory/warehouse_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["balances"] = (
            StockBalance.objects.filter(warehouse=self.object)
            .select_related("product")
            .order_by("product__name")
        )
        return ctx


class StockListView(LoginRequiredMixin, ListView):
    model = StockBalance
    template_name = "inventory/stock_list.html"
    paginate_by = 20
    context_object_name = "balances"

    def get_queryset(self):
        qs = (
            StockBalance.objects.filter(warehouse__in=warehouse_scope(self.request.user))
            .select_related("product", "product__category", "warehouse")
        )
        q = self.request.GET.get("q", "").strip()
        warehouse = self.request.GET.get("warehouse")
        category = self.request.GET.get("category")
        low = self.request.GET.get("low")
        if q:
            qs = qs.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q))
        if warehouse:
            qs = qs.filter(warehouse_id=warehouse)
        if category:
            qs = qs.filter(product__category_id=category)
        if low == "1":
            qs = qs.filter(quantity__lte=F("product__reorder_level"))
        return qs.order_by("product__name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["warehouses"] = warehouse_scope(self.request.user)
        ctx["categories"] = Category.objects.filter(is_active=True)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_warehouse"] = self.request.GET.get("warehouse", "")
        ctx["selected_category"] = self.request.GET.get("category", "")
        ctx["low"] = self.request.GET.get("low", "")
        return ctx


class MovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = "inventory/movement_list.html"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            StockMovement.objects.filter(warehouse__in=warehouse_scope(self.request.user))
            .select_related("warehouse", "destination_warehouse", "created_by")
            .prefetch_related("lines__product")
        )
        q = self.request.GET.get("q", "").strip()
        mtype = self.request.GET.get("type")
        warehouse = self.request.GET.get("warehouse")
        if q:
            qs = qs.filter(Q(reference__icontains=q) | Q(notes__icontains=q) | Q(lines__product__sku__icontains=q))
        if mtype:
            qs = qs.filter(movement_type=mtype)
        if warehouse:
            qs = qs.filter(Q(warehouse_id=warehouse) | Q(destination_warehouse_id=warehouse))
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["warehouses"] = warehouse_scope(self.request.user)
        ctx["types"] = StockMovement.MovementType.choices
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["selected_warehouse"] = self.request.GET.get("warehouse", "")
        return ctx


class MovementDetailView(LoginRequiredMixin, DetailView):
    model = StockMovement
    template_name = "inventory/movement_detail.html"
    queryset = StockMovement.objects.select_related(
        "warehouse", "destination_warehouse", "created_by", "purchase_order"
    ).prefetch_related("lines__product")

    def get_queryset(self):
        return super().get_queryset().filter(warehouse__in=warehouse_scope(self.request.user))


class MovementCreateView(StaffRequiredMixin, CreateView):
    template_name = "inventory/movement_form.html"
    form_class = StockMovementForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        mtype = self.request.GET.get("type")
        if mtype in StockMovement.MovementType.values:
            initial["movement_type"] = mtype
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = MovementLineFormSet(self.request.POST)
        else:
            ctx["formset"] = MovementLineFormSet()
        return ctx

    def form_valid(self, form):
        formset = MovementLineFormSet(self.request.POST)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        lines = []
        for line_form in formset:
            if not line_form.cleaned_data or line_form.cleaned_data.get("DELETE"):
                continue
            lines.append(
                {
                    "product": line_form.cleaned_data["product"],
                    "quantity": line_form.cleaned_data["quantity"],
                    "unit_cost": line_form.cleaned_data.get("unit_cost"),
                }
            )
        movement = form.save(commit=False)
        try:
            posted = post_movement(user=self.request.user, movement=movement, lines=lines)
        except StockError as exc:
            form.add_error(None, str(exc))
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        messages.success(self.request, "Stock movement posted.")
        return redirect(reverse("inventory:movement-detail", args=[posted.pk]))
