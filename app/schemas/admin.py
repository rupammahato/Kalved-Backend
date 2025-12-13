"""Admin schemas."""
from pydantic import BaseModel


class AdminAction(BaseModel):
    target_user_id: str
    action: str
