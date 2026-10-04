from django.urls import path

from apps.purchasing import views

app_name = "purchasing"

urlpatterns = [
    path("suppliers/", views.SupplierListView.as_view(), name="supplier-list"),
    path("suppliers/new/", views.SupplierCreateView.as_view(), name="supplier-create"),
    path("suppliers/<int:pk>/", views.SupplierDetailView.as_view(), name="supplier-detail"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier-update"),
    path("orders/", views.PurchaseOrderListView.as_view(), name="po-list"),
    path("orders/new/", views.PurchaseOrderCreateView.as_view(), name="po-create"),
    path("orders/<int:pk>/", views.PurchaseOrderDetailView.as_view(), name="po-detail"),
    path("orders/<int:pk>/edit/", views.PurchaseOrderUpdateView.as_view(), name="po-update"),
    path("orders/<int:pk>/<str:action>/", views.PurchaseOrderActionView.as_view(), name="po-action"),
]
