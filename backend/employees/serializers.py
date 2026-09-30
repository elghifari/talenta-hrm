from collections.abc import Mapping

from rest_framework import serializers

from .models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
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
        fields = ["id", "employee_code", "full_name"]
        read_only_fields = ["id"]
