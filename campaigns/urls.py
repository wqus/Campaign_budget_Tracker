from rest_framework.routers import DefaultRouter

from campaigns.views import CampaignViewSet

router = DefaultRouter()
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = router.urls
