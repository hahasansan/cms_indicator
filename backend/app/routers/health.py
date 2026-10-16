from datetime import datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"ok": True, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}