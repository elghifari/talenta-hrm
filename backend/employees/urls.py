from rest_framework.routers import SimpleRouter

from .views import EmployeeViewSet

router = SimpleRouter()
router.register("employees", EmployeeViewSet, basename="employee")
urlpatterns = router.urls
