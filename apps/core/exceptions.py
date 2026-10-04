from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    from apps.inventory.services import StockError
    from apps.purchasing.services import PurchasingError

    if isinstance(exc, (StockError, PurchasingError)):
        http_status = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
        return Response({"detail": str(exc)}, status=http_status)

    return exception_handler(exc, context)
