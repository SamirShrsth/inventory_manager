from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.mixins import StaffRequiredMixin
from apps.inventory.selectors import warehouse_scope
from apps.purchasing.forms import POLineFormSet, PurchaseOrderForm, ReceiveForm, SupplierForm
from apps.purchasing.models import PurchaseOrder, Supplier
from apps.purchasing.services import PurchasingError, cancel_order, generate_po_number, receive_order, submit_order


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = "purchasing/supplier_list.html"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(email__icontains=q))
        return qs


class SupplierCreateView(StaffRequiredMixin, CreateView):
    form_class = SupplierForm
    template_name = "purchasing/supplier_form.html"
    success_url = reverse_lazy("purchasing:supplier-list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier created.")
        return super().form_valid(form)


class SupplierUpdateView(StaffRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "purchasing/supplier_form.html"
    success_url = reverse_lazy("purchasing:supplier-list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier updated.")
        return super().form_valid(form)


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = "purchasing/supplier_detail.html"


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = "purchasing/po_list.html"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            PurchaseOrder.objects.filter(warehouse__in=warehouse_scope(self.request.user))
            .select_related("supplier", "warehouse", "created_by")
        )
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status")
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(supplier__name__icontains=q))
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = PurchaseOrder.Status.choices
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = "purchasing/po_detail.html"
    queryset = PurchaseOrder.objects.select_related("supplier", "warehouse", "created_by").prefetch_related(
        "lines__product"
    )

    def get_queryset(self):
        return super().get_queryset().filter(warehouse__in=warehouse_scope(self.request.user))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.status in {PurchaseOrder.Status.SUBMITTED, PurchaseOrder.Status.PARTIAL}:
            ctx["receive_form"] = ReceiveForm(purchase_order=self.object)
        return ctx


class PurchaseOrderCreateView(StaffRequiredMixin, CreateView):
    form_class = PurchaseOrderForm
    template_name = "purchasing/po_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = POLineFormSet(self.request.POST or None)
        return ctx

    def form_valid(self, form):
        formset = POLineFormSet(self.request.POST)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        po = form.save(commit=False)
        po.created_by = self.request.user
        po.number = generate_po_number()
        if not self.request.user.can_mutate_warehouse(po.warehouse):
            form.add_error("warehouse", "You are not assigned to this warehouse.")
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        po.save()
        formset.instance = po
        formset.save()
        messages.success(self.request, f"Purchase order {po.number} created.")
        return redirect(reverse("purchasing:po-detail", args=[po.pk]))


class PurchaseOrderUpdateView(StaffRequiredMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = "purchasing/po_form.html"

    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            warehouse__in=warehouse_scope(self.request.user),
            status=PurchaseOrder.Status.DRAFT,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = POLineFormSet(self.request.POST or None, instance=self.object)
        return ctx

    def form_valid(self, form):
        formset = POLineFormSet(self.request.POST, instance=self.object)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        po = form.save()
        formset.save()
        messages.success(self.request, "Purchase order updated.")
        return redirect(reverse("purchasing:po-detail", args=[po.pk]))


class PurchaseOrderActionView(StaffRequiredMixin, View):
    def post(self, request, pk, action):
        po = get_object_or_404(
            PurchaseOrder.objects.filter(warehouse__in=warehouse_scope(request.user)),
            pk=pk,
        )
        try:
            if action == "submit":
                submit_order(po)
                messages.success(request, "Purchase order submitted.")
            elif action == "cancel":
                cancel_order(po)
                messages.success(request, "Purchase order cancelled.")
            elif action == "receive":
                form = ReceiveForm(request.POST, purchase_order=po)
                if not form.is_valid():
                    messages.error(request, "Check receipt quantities.")
                    return redirect("purchasing:po-detail", pk=pk)
                receipts = []
                for field, value in form.cleaned_data.items():
                    if not value:
                        continue
                    line_id = int(field.replace("qty_", ""))
                    line = po.lines.get(pk=line_id)
                    receipts.append({"line": line, "quantity": value})
                receive_order(user=request.user, po=po, receipts=receipts)
                messages.success(request, "Goods received and stock updated.")
            else:
                messages.error(request, "Unknown action.")
        except PurchasingError as exc:
            messages.error(request, str(exc))
        return redirect("purchasing:po-detail", pk=pk)
