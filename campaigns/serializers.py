from decimal import Decimal

from rest_framework import serializers

from campaigns.models import Campaign, SpendTransaction


class SpendTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpendTransaction
        fields = ["id", "campaign", "amount", "idempotency_key", "created_at"]
        read_only_fields = fields


class CampaignSerializer(serializers.ModelSerializer):
    remaining_budget = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "advertiser_name",
            "status",
            "total_budget",
            "spent_total",
            "remaining_budget",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "spent_total", "created_at", "updated_at"]

    def validate_total_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("total_budget must be greater than zero.")
        return value


class CampaignSpendSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    idempotency_key = serializers.CharField(max_length=255)
