from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role())


class IsStaffOrAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.can_mutate())


class IsAuthenticatedReadOnlyOrStaff(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.can_mutate()


class IsAdminOrReadOnlyStaffWrite(BasePermission):
    """GET for authenticated users; writes for staff/admin; delete for admin."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return user.is_admin_role()
        return user.can_mutate()
