import uuid

from django.conf import settings
from django.db import models


class ContractDraft(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    employee = models.ForeignKey("employees.Employee", on_delete=models.PROTECT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_contract_drafts"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_contract_drafts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revision = models.PositiveIntegerField(default=1)
    pkwt_type = models.CharField(max_length=16)
    reference_version = models.CharField(max_length=80)
    template_sha256 = models.CharField(max_length=64)
    employee_snapshot = models.JSONField()
    source_unit = models.CharField(max_length=200, null=True, blank=True)
    job_default_key = models.CharField(max_length=1000, null=True, blank=True)
    values = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(revision__gte=1), name="contract_draft_positive_revision"
            )
        ]
        indexes = [models.Index(fields=["employee", "-updated_at", "-id"])]


class ContractDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(ContractDraft, on_delete=models.PROTECT, related_name="documents")
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField()
    reference_version = models.CharField(max_length=80)
    pkwt_type = models.CharField(max_length=16)
    template_sha256 = models.CharField(max_length=64)
    input_snapshot = models.JSONField()
    token_snapshot = models.JSONField()
    filename = models.CharField(max_length=200)
    mime_type = models.CharField(max_length=100)
    content_sha256 = models.CharField(max_length=64)
    content = models.BinaryField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(revision__gte=1), name="contract_document_positive_revision"
            ),
            models.UniqueConstraint(
                fields=["draft", "revision", "template_sha256"],
                name="unique_contract_document_revision",
            ),
        ]
