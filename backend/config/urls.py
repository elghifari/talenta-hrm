from accounts.views import SessionLoginView, SessionLogoutView, csrf, me
from django.conf import settings
from django.urls import include, path, re_path

from .views import health

urlpatterns = [
    path("api/health/", health),
    path("api/", include("employees.urls")),
    path("api/", include("audit.urls")),
    path("api/organization/", include("organization.urls")),
    path("api/auth/csrf/", csrf),
    path("api/auth/login/", SessionLoginView.as_view()),
    path("api/auth/me/", me),
    path("api/auth/logout/", SessionLogoutView.as_view()),
]

if getattr(settings, "FRONTEND_DEV_ENABLED", False):
    from .frontend import asset, spa

    urlpatterns += [
        path("assets/<path:name>", asset),
        re_path(r"^(?P<path>.*)$", spa),
    ]
