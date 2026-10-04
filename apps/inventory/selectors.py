from apps.inventory.models import Warehouse


def warehouse_scope(user):
    if not user.is_authenticated:
        return Warehouse.objects.none()
    if user.is_admin_role() or user.role == user.Roles.VIEWER:
        return Warehouse.objects.all()
    return Warehouse.objects.filter(assigned_users=user)
