from fastapi import APIRouter

from app.core.security import get_security_status

router = APIRouter(tags=["security"])


@router.get("/security/status")
def security_status() -> dict[str, object]:
    return get_security_status()
