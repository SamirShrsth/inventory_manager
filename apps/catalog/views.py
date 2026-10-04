from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.catalog.forms import CategoryForm, ProductForm
from apps.catalog.models import Category, Product
from apps.core.mixins import StaffRequiredMixin
from apps.inventory.models import StockBalance


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "catalog/product_list.html"
    paginate_by = 20
    context_object_name = "products"

    def get_queryset(self):
        qs = Product.objects.select_related("category").annotate(on_hand=Sum("balances__quantity"))
        q = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category")
        active = self.request.GET.get("active")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
        if category:
            qs = qs.filter(category_id=category)
        if active in {"1", "0"}:
            qs = qs.filter(is_active=active == "1")
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.filter(is_active=True)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_category"] = self.request.GET.get("category", "")
        ctx["selected_active"] = self.request.GET.get("active", "")
        return ctx


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = "catalog/product_detail.html"
    queryset = Product.objects.select_related("category")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["balances"] = (
            StockBalance.objects.filter(product=self.object)
            .select_related("warehouse")
            .order_by("warehouse__name")
        )
        ctx["supplier_links"] = self.object.supplier_links.select_related("supplier")
        return ctx


class ProductCreateView(StaffRequiredMixin, CreateView):
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    success_url = reverse_lazy("catalog:product-list")

    def form_valid(self, form):
        messages.success(self.request, "Product created.")
        return super().form_valid(form)


class ProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    success_url = reverse_lazy("catalog:product-list")

    def form_valid(self, form):
        messages.success(self.request, "Product updated.")
        return super().form_valid(form)


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "catalog/category_list.html"
    paginate_by = 20


class CategoryCreateView(StaffRequiredMixin, CreateView):
    form_class = CategoryForm
    template_name = "catalog/category_form.html"
    success_url = reverse_lazy("catalog:category-list")

    def form_valid(self, form):
        messages.success(self.request, "Category created.")
        return super().form_valid(form)


class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "catalog/category_form.html"
    success_url = reverse_lazy("catalog:category-list")

    def form_valid(self, form):
        messages.success(self.request, "Category updated.")
        return super().form_valid(form)
