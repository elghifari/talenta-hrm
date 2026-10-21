from collections.abc import Mapping

from accounts.capabilities import employee_capabilities
from rest_framework import serializers

from .models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None and not employee_capabilities(request.user)["employees_write"]:
            return {
                key: field
                for key, field in fields.items()
                if key in {"id", "employee_code", "full_name"}
            }
        return fields

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            writable = {name for name, field in self.fields.items() if not field.read_only}
            rejected = set(data) - writable
            if rejected:
                raise serializers.ValidationError(
                    {name: ["Unknown or read-only field."] for name in sorted(rejected)}
                )
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        for name, value in validated_data.items():
            setattr(instance, name, value)
        instance.save(update_fields=list(validated_data))
        return instance

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_code",
            "full_name",
            "date_of_birth",
            "job_title",
            "level",
            "start_date",
            "contract_expiry",
        ]
        read_only_fields = ["id"]
