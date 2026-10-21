from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .import_service import batch_response, create_preview, get_batch
from .permissions import HRPermission


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
