from django.urls import path

from .views import (
    DocumentsView,
    DownloadView,
    DraftDetailView,
    DraftListView,
    GenerateView,
    ReferencesView,
)

urlpatterns = [
    path("contract-references/", ReferencesView.as_view()),
    path("contract-drafts/", DraftListView.as_view()),
    path("contract-drafts/<uuid:pk>/", DraftDetailView.as_view()),
    path("contract-drafts/<uuid:pk>/generate/", GenerateView.as_view()),
    path("contract-drafts/<uuid:pk>/documents/", DocumentsView.as_view()),
    path("contract-documents/<uuid:pk>/download/", DownloadView.as_view()),
]
