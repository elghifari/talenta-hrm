from collections.abc import Mapping

from rest_framework import serializers

from .models import Branch, Division


class ReferenceSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        writable = {name for name, field in self.fields.items() if not field.read_only}
        if isinstance(data, Mapping) and set(data) - writable:
            raise serializers.ValidationError({"name": ["Kolom tidak dikenal atau hanya-baca."]})
        return super().to_internal_value(data)

    def validate_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Nama wajib diisi.")
        return value

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", None))
        matches = self.Meta.model.objects.filter(name__iexact=name)
        if self.Meta.model is Division:
            branch = attrs.get("branch", getattr(self.instance, "branch", None))
            if self.instance and branch.pk != self.instance.branch_id:
                raise serializers.ValidationError(
                    {
                        "branch": [
                            "Cabang pemilik tidak dapat diubah. Buat divisi baru di cabang tujuan."
                        ]
                    }
                )
            matches = matches.filter(branch=branch)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError({"name": ["Nama sudah digunakan."]})
        return attrs

    class Meta:
        fields = ["id", "name"]
        read_only_fields = ["id"]


class BranchSerializer(ReferenceSerializer):
    class Meta(ReferenceSerializer.Meta):
        model = Branch


class DivisionSerializer(ReferenceSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if validated_data:
            instance.save(update_fields=list(validated_data))
        instance.refresh_from_db()
        return instance

    class Meta(ReferenceSerializer.Meta):
        model = Division
        fields = ["id", "name", "branch", "branch_name", "kinerja_enabled", "pelimpahan_enabled"]
        read_only_fields = ["id", "kinerja_enabled", "pelimpahan_enabled"]
