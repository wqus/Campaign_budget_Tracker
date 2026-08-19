import logging

from django.db import transaction

from campaigns.exceptions import CampaignNotActivatableError, InsufficientBudgetError
from campaigns.models import Campaign, SpendTransaction

logger = logging.getLogger(__name__)


@transaction.atomic
def spend_budget(*, campaign_id, amount, idempotency_key) -> SpendTransaction:
    existing = SpendTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        logger.info(
            "Idempotent replay for key=%s on campaign=%s — returning existing transaction",
            idempotency_key,
            campaign_id,
        )
        return existing

    campaign = Campaign.objects.select_for_update().get(id=campaign_id)

    if campaign.spent_total + amount > campaign.total_budget:
        logger.warning(
            "Rejected spend of %s on campaign=%s: remaining=%s",
            amount,
            campaign_id,
            campaign.remaining_budget,
        )
        raise InsufficientBudgetError(
            f"Spend of {amount} exceeds remaining budget of {campaign.remaining_budget}."
        )

    campaign.spent_total += amount
    if campaign.spent_total >= campaign.total_budget:
        campaign.status = Campaign.Status.FINISHED

    campaign.save(update_fields=["spent_total", "status", "updated_at"])

    try:
        txn = SpendTransaction.objects.create(
            campaign=campaign, amount=amount, idempotency_key=idempotency_key
        )
    except Exception:
        logger.info("Idempotency key collision on insert for key=%s — reusing winner", idempotency_key)
        return SpendTransaction.objects.get(idempotency_key=idempotency_key)

    logger.info("Spent %s on campaign=%s (remaining=%s)", amount, campaign_id, campaign.remaining_budget)
    return txn


@transaction.atomic
def activate_campaign(*, campaign_id) -> Campaign:
    campaign = Campaign.objects.select_for_update().get(id=campaign_id)

    if campaign.remaining_budget <= 0:
        raise CampaignNotActivatableError("Campaign has no remaining budget.")

    campaign.status = Campaign.Status.ACTIVE
    campaign.save(update_fields=["status", "updated_at"])
    return campaign


@transaction.atomic
def pause_campaign(*, campaign_id) -> Campaign:
    campaign = Campaign.objects.select_for_update().get(id=campaign_id)
    campaign.status = Campaign.Status.DRAFT
    campaign.save(update_fields=["status", "updated_at"])
    return campaign
