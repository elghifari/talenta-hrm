from rest_framework import serializers

from .models import CompensationAssignment


class CompensationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompensationAssignment
        fields = ["id", "component_code", "amount", "effective_from", "effective_until"]
        read_only_fields = fields
