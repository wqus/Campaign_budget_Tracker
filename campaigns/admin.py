from django.contrib import admin

from campaigns.models import Campaign, SpendTransaction


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "advertiser_name", "status", "total_budget", "spent_total", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "advertiser_name"]
    readonly_fields = ["id", "spent_total", "created_at", "updated_at"]


@admin.register(SpendTransaction)
class SpendTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "campaign", "amount", "idempotency_key", "created_at"]
    readonly_fields = ["id", "created_at"]
    search_fields = ["idempotency_key"]
