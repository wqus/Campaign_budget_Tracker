import factory

from campaigns.models import Campaign


class CampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Campaign

    name = factory.Sequence(lambda n: f"Campaign {n}")
    advertiser_name = factory.Faker("company")
    total_budget = "1000.00"
    status = Campaign.Status.DRAFT
