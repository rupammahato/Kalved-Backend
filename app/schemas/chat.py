from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class ChatRoomBase(BaseModel):
    id: int
    appointment_id: Optional[int]
    doctor_id: int
    patient_id: int
    room_type: str
    room_status: str
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    unread_count_doctor: int
    unread_count_patient: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageBase(BaseModel):
    id: int
    chat_room_id: int
    sender_id: int
    message_text: str
    message_type: str
    attachment_url: Optional[str]
    attachment_type: Optional[str]
    is_read: bool
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    read_at: Optional[datetime]
    edited_at: Optional[datetime]
    deleted_at: Optional[datetime]
    replied_to_message_id: Optional[int]

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    message_text: str = Field(..., max_length=4000)
    message_type: str = Field("text", description="text, image, file, system")
    replied_to_message_id: Optional[int] = None


class ChatMessageUpdate(BaseModel):
    message_text: str = Field(..., max_length=4000)


class ChatMessageResponse(ChatMessageBase):
    pass


class ChatHistoryResponse(BaseModel):
    items: List[ChatMessageResponse]
    total: int


class ChatRoomResponse(ChatRoomBase):
    pass


class ReadReceiptRequest(BaseModel):
    up_to_message_id: int


class SearchMessagesQuery(BaseModel):
    query: Optional[str] = None
    sender_id: Optional[int] = None
    from_ts: Optional[datetime] = None
    to_ts: Optional[datetime] = None
