from rest_framework import serializers

from .models import ContractDocument, ContractDraft


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"detail": ["Objek JSON diperlukan."]})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: ["Isian tidak dikenal."] for key in unknown})
        return super().to_internal_value(data)


class CreateDraftInput(StrictSerializer):
    id = serializers.UUIDField()
    employee = serializers.UUIDField()
    source_unit = serializers.CharField(max_length=200, allow_null=True, required=False)
    job_default_key = serializers.CharField(max_length=1000, allow_null=True, required=False)
    values = serializers.JSONField(default=dict)


class UpdateDraftInput(StrictSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    source_unit = serializers.CharField(max_length=200, allow_null=True, required=False)
    job_default_key = serializers.CharField(max_length=1000, allow_null=True, required=False)
    values = serializers.JSONField(required=False)


class GenerateInput(StrictSerializer):
    expected_revision = serializers.IntegerField(min_value=1)


class DraftMetadata(serializers.ModelSerializer):
    class Meta:
        model = ContractDraft
        fields = [
            "id",
            "employee",
            "pkwt_type",
            "revision",
            "reference_version",
            "template_sha256",
            "created_at",
            "updated_at",
        ]


class DraftDetail(serializers.ModelSerializer):
    class Meta:
        model = ContractDraft
        fields = DraftMetadata.Meta.fields + [
            "employee_snapshot",
            "source_unit",
            "job_default_key",
            "values",
        ]


class DocumentReceipt(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    def get_download_url(self, obj):
        return f"/api/contract-documents/{obj.id}/download/"

    class Meta:
        model = ContractDocument
        fields = [
            "id",
            "draft",
            "revision",
            "template_sha256",
            "filename",
            "content_sha256",
            "generated_at",
            "download_url",
        ]
