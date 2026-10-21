import csv
import io

from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .import_service import batch_response, commit_batch, create_preview, get_batch
from .imports import COLUMNS
from .permissions import HRPermission


class ImportTemplateView(APIView):
    permission_classes = [IsAuthenticated, HRPermission]

    def get(self, request):
        output = io.StringIO(newline="")
        csv.writer(output).writerow(COLUMNS)
        response = HttpResponse(
            "\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = 'attachment; filename="template-karyawan.csv"'
        return response


class ImportPreviewView(APIView):
    permission_classes = [IsAuthenticated, HRPermission]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if set(request.data) != {"file"} or len(request.FILES.getlist("file")) != 1:
            raise ValidationError({"file": ["Pilih satu file CSV."]})
        return Response(batch_response(create_preview(request, request.FILES["file"])), status=201)


class ImportBatchView(APIView):
    permission_classes = [IsAuthenticated, HRPermission]

    def get(self, request, batch_id):
        return Response(batch_response(get_batch(request, batch_id)))


class ImportConfirmView(APIView):
    permission_classes = [IsAuthenticated, HRPermission]
    parser_classes = [JSONParser]

    def post(self, request, batch_id):
        if request.data != {}:
            raise ValidationError(
                {"detail": "Konfirmasi tidak menerima perubahan data dari klien."}
            )
        return Response(batch_response(commit_batch(request, batch_id)))
