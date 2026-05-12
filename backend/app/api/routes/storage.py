from fastapi import APIRouter

from app.db.database import get_database_path
from app.services.deals_service import deals_service

router = APIRouter(tags=["storage"])


@router.get("/storage/status")
def storage_status() -> dict[str, object]:
    database_path = get_database_path()

    return {
        "status": "ok",
        "type": "sqlite",
        "databasePath": str(database_path),
        "exists": database_path.exists(),
        "dealCount": deals_service.count_deals(),
    }
