from fastapi import APIRouter

from app.models.deal import RatesResponse
from app.services.deals_service import DEMO_RATES

router = APIRouter(tags=["settings"])


@router.get("/settings/rates", response_model=RatesResponse, response_model_by_alias=True)
def rates() -> RatesResponse:
    return RatesResponse(
        base_currency="USD",
        rates=DEMO_RATES,
        note="Demo rates only. Production must use a real exchange-rate provider.",
    )
