import pytest
from rest_framework.test import APIClient

from campaigns.tests.factories import CampaignFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def campaign(db):
    return CampaignFactory(total_budget="1000.00")
