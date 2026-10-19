from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .capabilities import employee_capabilities


@require_GET
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


class SessionLoginView(LoginView):
    http_method_names = ["post", "options"]

    def form_valid(self, form):
        login(self.request, form.get_user())
        return JsonResponse({"detail": "Signed in"})

    def form_invalid(self, form):
        return JsonResponse({"detail": "Invalid email or password"}, status=400)


class SessionLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        logout(request)
        return JsonResponse({}, status=204)


@api_view(["GET"])
def me(request):
    return Response(
        {
            "id": request.user.pk,
            "email": request.user.email,
            "capabilities": employee_capabilities(request.user),
        }
    )
