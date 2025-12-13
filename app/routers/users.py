"""User profile endpoints (skeleton)."""
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_profile():
    return {"msg": "get current user profile (implement)"}
