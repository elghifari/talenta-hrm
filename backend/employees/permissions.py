from accounts.capabilities import employee_capabilities
from rest_framework.permissions import SAFE_METHODS, BasePermission


class HRPermission(BasePermission):
    def has_permission(self, request, view):
        return employee_capabilities(request.user)["employees_write"]


class EmployeePermission(BasePermission):
    def has_permission(self, request, view):
        capabilities = employee_capabilities(request.user)
        key = "employees_read" if request.method in SAFE_METHODS else "employees_write"
        return capabilities[key]
