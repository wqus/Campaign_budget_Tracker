from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from campaigns import services
from campaigns.models import Campaign
from campaigns.serializers import (
    CampaignSerializer,
    CampaignSpendSerializer,
)


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["status", "advertiser_name"]
    search_fields = ["name", "advertiser_name"]
    ordering_fields = ["created_at", "total_budget", "spent_total"]

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        campaign = services.activate_campaign(campaign_id=pk)
        return Response(CampaignSerializer(campaign).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        campaign = services.pause_campaign(campaign_id=pk)
        return Response(CampaignSerializer(campaign).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def spend(self, request, pk=None):
        input_serializer = CampaignSpendSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        txn = services.spend_budget(
            campaign_id=pk,
            amount=input_serializer.validated_data["amount"],
            idempotency_key=input_serializer.validated_data["idempotency_key"],
        )
        campaign = Campaign.objects.get(id=pk)
        return Response(
            {
                "transaction_id": txn.id,
                "amount": txn.amount,
                "campaign": CampaignSerializer(campaign).data,
            },
            status=status.HTTP_201_CREATED,
        )
