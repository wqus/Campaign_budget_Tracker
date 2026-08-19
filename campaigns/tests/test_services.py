from decimal import Decimal

import pytest

from campaigns import services
from campaigns.exceptions import CampaignNotActivatableError, InsufficientBudgetError
from campaigns.models import Campaign, SpendTransaction
from campaigns.tests.factories import CampaignFactory

pytestmark = pytest.mark.django_db


class TestSpendBudget:
    def test_successful_spend_reduces_remaining_budget(self, campaign):
        txn = services.spend_budget(
            campaign_id=campaign.id, amount=Decimal("100.00"), idempotency_key="key-1"
        )

        campaign.refresh_from_db()
        assert txn.amount == Decimal("100.00")
        assert campaign.spent_total == Decimal("100.00")
        assert campaign.remaining_budget == Decimal("900.00")

    def test_spend_over_budget_is_rejected(self, campaign):
        with pytest.raises(InsufficientBudgetError):
            services.spend_budget(
                campaign_id=campaign.id, amount=Decimal("2000.00"), idempotency_key="key-1"
            )

        campaign.refresh_from_db()
        assert campaign.spent_total == Decimal("0.00")
        assert SpendTransaction.objects.count() == 0

    def test_repeated_idempotency_key_does_not_double_charge(self, campaign):
        services.spend_budget(campaign_id=campaign.id, amount=Decimal("100.00"), idempotency_key="dup-key")
        services.spend_budget(campaign_id=campaign.id, amount=Decimal("100.00"), idempotency_key="dup-key")

        campaign.refresh_from_db()
        assert campaign.spent_total == Decimal("100.00")
        assert SpendTransaction.objects.filter(idempotency_key="dup-key").count() == 1

    def test_exhausting_budget_marks_campaign_finished(self, campaign):
        services.spend_budget(campaign_id=campaign.id, amount=Decimal("1000.00"), idempotency_key="key-1")

        campaign.refresh_from_db()
        assert campaign.status == Campaign.Status.FINISHED
        assert campaign.remaining_budget == Decimal("0.00")

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_spends_never_overdraw_budget(self):
        """Two threads race to spend more than the remaining budget allows.

        select_for_update() inside the service should serialise access
        to the campaign row so exactly one of the two spends succeeds
        (60 + 60 = 120 exceeds a 100 budget, so only one may go through).

        This test needs real row-level locking across separate DB
        connections, which SQLite does not provide (it locks the whole
        file and separate threads simply raise "database is locked"
        rather than queuing). It is skipped on SQLite and meant to run
        against Postgres — e.g. via `docker-compose run web pytest`,
        or in CI where DATABASE_URL points at a Postgres service.
        """
        from django.db import connection

        if connection.vendor != "postgresql":
            pytest.skip("Row-locking race condition only verifiable against Postgres; see docstring.")

        import threading

        from django.db import connections

        campaign = CampaignFactory(total_budget=Decimal("100.00"))

        results = {}

        def attempt(key, amount):
            try:
                services.spend_budget(campaign_id=campaign.id, amount=amount, idempotency_key=key)
                results[key] = "success"
            except InsufficientBudgetError:
                results[key] = "rejected"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("t1", Decimal("60.00")))
        t2 = threading.Thread(target=attempt, args=("t2", Decimal("60.00")))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        campaign.refresh_from_db()
        outcomes = sorted(results.values())
        assert outcomes == ["rejected", "success"]
        assert campaign.spent_total == Decimal("60.00")


class TestActivateCampaign:
    def test_activate_with_budget_succeeds(self, campaign):
        updated = services.activate_campaign(campaign_id=campaign.id)
        assert updated.status == Campaign.Status.ACTIVE

    def test_activate_with_no_remaining_budget_fails(self):
        exhausted = CampaignFactory(total_budget=Decimal("50.00"), spent_total=Decimal("50.00"))
        with pytest.raises(CampaignNotActivatableError):
            services.activate_campaign(campaign_id=exhausted.id)
