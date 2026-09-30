from accounts.views import SessionLoginView, SessionLogoutView, csrf, me
from django.urls import include, path

from .views import health

urlpatterns = [
    path("api/health/", health),
    path("api/", include("employees.urls")),
    path("api/auth/csrf/", csrf),
    path("api/auth/login/", SessionLoginView.as_view()),
    path("api/auth/me/", me),
    path("api/auth/logout/", SessionLogoutView.as_view()),
]
