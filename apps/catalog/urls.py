from django.urls import path

from apps.catalog import views

app_name = "catalog"

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/new/", views.ProductCreateView.as_view(), name="product-create"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product-update"),
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("categories/new/", views.CategoryCreateView.as_view(), name="category-create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category-update"),
]
