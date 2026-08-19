from rest_framework.views import exception_handler


class InsufficientBudgetError(Exception):
    """Списание превышает оставшийся бюджет кампании."""


class CampaignNotActivatableError(Exception):
    """Кампанию нельзя активировать (например, бюджет исчерпан)."""


def custom_exception_handler(exc, context):
    from rest_framework.response import Response
    from rest_framework import status

    if isinstance(exc, InsufficientBudgetError):
        return Response({"detail": str(exc) or "Insufficient budget."}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, CampaignNotActivatableError):
        return Response({"detail": str(exc) or "Campaign cannot be activated."}, status=status.HTTP_400_BAD_REQUEST)

    return exception_handler(exc, context)