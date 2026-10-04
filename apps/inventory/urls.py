from django.urls import path

from apps.inventory import views

app_name = "inventory"

urlpatterns = [
    path("warehouses/", views.WarehouseListView.as_view(), name="warehouse-list"),
    path("warehouses/new/", views.WarehouseCreateView.as_view(), name="warehouse-create"),
    path("warehouses/<int:pk>/", views.WarehouseDetailView.as_view(), name="warehouse-detail"),
    path("warehouses/<int:pk>/edit/", views.WarehouseUpdateView.as_view(), name="warehouse-update"),
    path("stock/", views.StockListView.as_view(), name="stock-list"),
    path("movements/", views.MovementListView.as_view(), name="movement-list"),
    path("movements/new/", views.MovementCreateView.as_view(), name="movement-create"),
    path("movements/<int:pk>/", views.MovementDetailView.as_view(), name="movement-detail"),
]
