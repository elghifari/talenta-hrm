from rest_framework.routers import SimpleRouter

from .views import BranchViewSet, DivisionViewSet

router = SimpleRouter()
router.register("branches", BranchViewSet, basename="branch")
router.register("divisions", DivisionViewSet, basename="division")
urlpatterns = router.urls
