from rest_framework.permissions import SAFE_METHODS, BasePermission


class HRPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name="HR").exists()


class EmployeePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.groups.filter(name="HR").exists():
            return True
        return (
            request.method in SAFE_METHODS
            and request.user.groups.filter(name="KEPALA_UNIT").exists()
        )
