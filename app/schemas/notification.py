from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    id: int
    user_id: int
    notification_type: str
    title: str
    body: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True  # orm_mode=True if using Pydantic v1


class NotificationListItem(NotificationBase):
    read_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    items: List[NotificationListItem]
    total: int


class NotificationMarkReadRequest(BaseModel):
    read: bool = Field(True, description="Mark notification as read (true) or unread (false)")


class NotificationPreferencesBase(BaseModel):
    appointment_reminders: bool = True
    appointment_reminder_hours: int = 24
    prescription_notifications: bool = True
    review_request_notifications: bool = True
    message_notifications: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True


class NotificationPreferencesResponse(NotificationPreferencesBase):
    user_id: int


class NotificationPreferencesUpdate(NotificationPreferencesBase):
    pass
