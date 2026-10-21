from django.urls import path
from rest_framework.routers import SimpleRouter

from .import_views import ImportBatchView, ImportPreviewView
from .views import EmployeeViewSet

router = SimpleRouter()
router.register("employees", EmployeeViewSet, basename="employee")
urlpatterns = [
    path("employees/import-preview/", ImportPreviewView.as_view()),
    path("employees/imports/<uuid:batch_id>/", ImportBatchView.as_view()),
] + router.urls
