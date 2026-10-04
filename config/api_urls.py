from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.catalog.viewsets import CategoryViewSet, ProductViewSet
from apps.inventory.viewsets import StockBalanceViewSet, StockMovementViewSet, WarehouseViewSet
from apps.purchasing.viewsets import PurchaseOrderViewSet, SupplierViewSet
from apps.users.api_views import ChangePasswordView, MeView, RegisterView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="api-users")
router.register("categories", CategoryViewSet, basename="api-categories")
router.register("products", ProductViewSet, basename="api-products")
router.register("suppliers", SupplierViewSet, basename="api-suppliers")
router.register("warehouses", WarehouseViewSet, basename="api-warehouses")
router.register("stock", StockBalanceViewSet, basename="api-stock")
router.register("movements", StockMovementViewSet, basename="api-movements")
router.register("purchase-orders", PurchaseOrderViewSet, basename="api-purchase-orders")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="api-token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("auth/me/", MeView.as_view(), name="api-me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="api-change-password"),
    path("schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("", include(router.urls)),
]
