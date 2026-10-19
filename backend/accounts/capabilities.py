def employee_capabilities(user):
    roles = set(user.groups.values_list("name", flat=True)) if user.is_authenticated else set()
    return {
        "employees_read": "HR" in roles or "KEPALA_UNIT" in roles,
        "employees_write": "HR" in roles,
    }
