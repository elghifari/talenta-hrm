import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import AuditEvent
from .permissions import CanReadAudit
from .presentation import ACTIONS, present_events


class AuditPagination(PageNumberPagination):
    page_size = 50
    last_page_strings = ()


def filter_events(events, params):
    actor = params.get("actor", "").strip()
    action = params.get("action", "")
    if len(actor) > 254:
        raise ValidationError({"actor": "Email pelaku terlalu panjang."})
    if action and action not in ACTIONS:
        raise ValidationError({"action": "Aktivitas tidak dikenali."})
    page = params.get("page", "1")
    if len(page) > 10 or not re.fullmatch(r"[1-9][0-9]*", page):
        raise ValidationError({"page": "Nomor halaman tidak valid."})
    dates = {}
    for key in ("date_from", "date_to"):
        value = params.get(key, "")
        if not value:
            continue
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError
            dates[key] = date.fromisoformat(value)
            if key == "date_to":
                dates[key] + timedelta(days=1)
        except (ValueError, OverflowError):
            raise ValidationError({key: "Tanggal tidak valid."}) from None
    if dates.get("date_from", date.min) > dates.get("date_to", date.max):
        raise ValidationError({"date_to": "Tanggal akhir harus setelah tanggal awal."})
    jakarta = ZoneInfo("Asia/Jakarta")
    if actor:
        events = events.filter(actor__email__icontains=actor)
    if action:
        events = events.filter(action=action)
    if "date_from" in dates:
        events = events.filter(
            created_at__gte=datetime.combine(dates["date_from"], time.min, jakarta)
        )
    if "date_to" in dates:
        upper = datetime.combine(dates["date_to"] + timedelta(days=1), time.min, jakarta)
        events = events.filter(created_at__lt=upper)
    return events


class AuditEventList(APIView):
    permission_classes = [CanReadAudit]

    def get(self, request):
        events = AuditEvent.objects.select_related("actor").order_by("-created_at", "-pk")
        events = filter_events(events, request.query_params)
        paginator = AuditPagination()
        page = paginator.paginate_queryset(events, request, view=self)
        response = paginator.get_paginated_response(present_events(page))
        response["Cache-Control"] = "no-store"
        return response
