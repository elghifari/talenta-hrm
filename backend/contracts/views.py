from io import BytesIO
from uuid import UUID

from django.core.exceptions import RequestDataTooBig
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import MAX_REQUEST_BYTES
from .fields import field_spec
from .models import ContractDocument, ContractDraft
from .permissions import ContractHRPermission
from .references import KINDS, ReferenceUnavailable, load_reference_bundle
from .serializers import (
    CreateDraftInput,
    DocumentReceipt,
    DraftDetail,
    DraftMetadata,
    GenerateInput,
    UpdateDraftInput,
)
from .services import create_draft, generate_document, update_draft


class BodyTooLarge(APIException):
    status_code = 413
    default_detail = {"code": "body_too_large"}


class ContractView(APIView):
    permission_classes = [ContractHRPermission]

    def initial(self, request, *args, **kwargs):
        if request.method in {"POST", "PATCH"}:
            try:
                if len(request.body) > MAX_REQUEST_BYTES:
                    raise BodyTooLarge()
            except RequestDataTooBig as exc:
                raise BodyTooLarge() from exc
        super().initial(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


def input_data(serializer_class, request):
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class ReferencesView(ContractView):
    def get(self, request):
        fields = {kind: field_spec(kind) for kind in sorted(KINDS)}
        try:
            bundle = load_reference_bundle(request.query_params.get("version") or None)
        except ReferenceUnavailable:
            return Response(
                {
                    "available": False,
                    "version": None,
                    "templates": {},
                    "units": [],
                    "jobs": [],
                    "fields": fields,
                }
            )
        return Response(
            {
                "available": True,
                "version": bundle.version,
                "templates": {
                    kind: {"sha256": bundle.template_sha256(kind)} for kind in sorted(KINDS)
                },
                "units": [dict(row) for row in bundle.units.values()],
                "jobs": [dict(row) for row in bundle.jobs.values()],
                "fields": fields,
            }
        )


class DraftListView(ContractView):
    def get(self, request):
        try:
            employee = UUID(request.query_params["employee"])
            raw_page = request.query_params.get("page", "1")
            if not raw_page.isascii() or not raw_page.isdecimal():
                raise ValueError()
            page = int(raw_page)
            if page < 1:
                raise ValueError()
        except (KeyError, ValueError, TypeError) as exc:
            raise ValidationError(
                {"detail": ["Employee UUID dan halaman valid diperlukan."]}
            ) from exc
        rows = ContractDraft.objects.filter(employee_id=employee).order_by("-updated_at", "-id")
        return Response(
            {
                "results": DraftMetadata(rows[(page - 1) * 50 : page * 50], many=True).data,
                "count": rows.count(),
                "page": page,
            }
        )

    def post(self, request):
        data = input_data(CreateDraftInput, request)
        draft = create_draft(
            actor=request.user, draft_id=data.pop("id"), employee_id=data.pop("employee"), **data
        )
        return Response(DraftDetail(draft).data, status=201)


class DraftDetailView(ContractView):
    def get(self, request, pk):
        return Response(DraftDetail(get_object_or_404(ContractDraft, pk=pk)).data)

    def patch(self, request, pk):
        data = input_data(UpdateDraftInput, request)
        draft = update_draft(
            actor=request.user,
            draft_id=pk,
            expected_revision=data.pop("expected_revision"),
            changes=data,
        )
        return Response(DraftDetail(draft).data)


class GenerateView(ContractView):
    def post(self, request, pk):
        data = input_data(GenerateInput, request)
        doc = generate_document(actor=request.user, draft_id=pk, **data)
        return Response(DocumentReceipt(doc).data)


class DocumentsView(ContractView):
    def get(self, request, pk):
        draft = get_object_or_404(ContractDraft, pk=pk)
        rows = draft.documents.defer("content", "input_snapshot", "token_snapshot").order_by(
            "-generated_at", "-id"
        )
        return Response({"results": DocumentReceipt(rows, many=True).data})


class DownloadView(ContractView):
    def get(self, request, pk):
        doc = get_object_or_404(ContractDocument, pk=pk)
        response = FileResponse(
            BytesIO(bytes(doc.content)),
            as_attachment=True,
            filename=doc.filename,
            content_type=doc.mime_type,
        )
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
