from accounts.capabilities import employee_capabilities
from rest_framework.permissions import BasePermission


class CanReadAudit(BasePermission):
    def has_permission(self, request, view):
        return employee_capabilities(request.user)["audit_read"]
