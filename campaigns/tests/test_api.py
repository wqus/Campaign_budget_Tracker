from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from campaigns.models import Campaign
from campaigns.tests.factories import CampaignFactory

pytestmark = pytest.mark.django_db


class TestCampaignCRUD:
    def test_create_campaign(self, api_client):
        url = reverse("campaign-list")
        payload = {"name": "Summer Sale", "advertiser_name": "Acme Corp", "total_budget": "500.00"}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == Campaign.Status.DRAFT
        assert response.data["remaining_budget"] == "500.00"

    def test_create_campaign_rejects_non_positive_budget(self, api_client):
        url = reverse("campaign-list")
        payload = {"name": "Bad Campaign", "advertiser_name": "Acme", "total_budget": "0.00"}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "total_budget" in response.data

    def test_list_campaigns_can_filter_by_status(self, api_client):
        CampaignFactory(status=Campaign.Status.ACTIVE)
        CampaignFactory(status=Campaign.Status.DRAFT)

        response = api_client.get(reverse("campaign-list"), {"status": "active"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["status"] == "active"


class TestCampaignSpendEndpoint:
    def test_spend_success(self, api_client, campaign):
        url = reverse("campaign-spend", args=[campaign.id])

        response = api_client.post(url, {"amount": "150.00", "idempotency_key": "order-1"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["campaign"]["spent_total"] == "150.00"
        assert response.data["campaign"]["remaining_budget"] == "850.00"

    def test_spend_over_budget_returns_400(self, api_client, campaign):
        url = reverse("campaign-spend", args=[campaign.id])

        response = api_client.post(url, {"amount": "9999.00", "idempotency_key": "order-2"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        campaign.refresh_from_db()
        assert campaign.spent_total == Decimal("0.00")

    def test_repeated_request_is_idempotent(self, api_client, campaign):
        url = reverse("campaign-spend", args=[campaign.id])
        payload = {"amount": "100.00", "idempotency_key": "retry-key"}

        first = api_client.post(url, payload, format="json")
        second = api_client.post(url, payload, format="json")

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_201_CREATED
        assert first.data["transaction_id"] == second.data["transaction_id"]

        campaign.refresh_from_db()
        assert campaign.spent_total == Decimal("100.00")

    def test_spend_requires_idempotency_key(self, api_client, campaign):
        url = reverse("campaign-spend", args=[campaign.id])

        response = api_client.post(url, {"amount": "100.00"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "idempotency_key" in response.data


class TestCampaignActivateEndpoint:
    def test_activate_succeeds_when_budget_remains(self, api_client, campaign):
        url = reverse("campaign-activate", args=[campaign.id])

        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == Campaign.Status.ACTIVE

    def test_activate_fails_when_budget_exhausted(self, api_client):
        exhausted = CampaignFactory(total_budget=Decimal("10.00"), spent_total=Decimal("10.00"))
        url = reverse("campaign-activate", args=[exhausted.id])

        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
