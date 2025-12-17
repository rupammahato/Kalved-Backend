from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.chat import (
    ChatRoomResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatMessageCreate,
    ChatMessageUpdate,
    ReadReceiptRequest,
)
from app.services.chat_service import ChatService
from app.services.storage_service import upload_chat_attachment
from app.models.chat import ChatRoom

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/", response_model=list[ChatRoomResponse])
def list_my_rooms(
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rooms = ChatService.list_user_rooms(db, user_id=current_user["sub"], skip=skip, limit=limit)
    return [ChatRoomResponse.from_orm(r) for r in rooms]


@router.get("/{room_id}/messages", response_model=ChatHistoryResponse)
def get_chat_history(
    room_id: int,
    skip: int = 0,
    limit: int = 50,
    query: Optional[str] = Query(None),
    sender_id: Optional[int] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Basic access check
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if current_user["sub"] not in (room.doctor_id, room.patient_id):
        raise HTTPException(status_code=403, detail="Not allowed")

    items, total = ChatService.list_messages(
        db=db,
        room_id=room_id,
        skip=skip,
        limit=limit,
        query=query,
        sender_id=sender_id,
    )
    return ChatHistoryResponse(
        items=[ChatMessageResponse.from_orm(m) for m in items],
        total=total,
    )


@router.post("/{room_id}/messages", response_model=ChatMessageResponse)
def send_message_http(
    room_id: int,
    payload: ChatMessageCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        msg = ChatService.create_message(
            db=db,
            room_id=room_id,
            sender_id=current_user["sub"],
            payload=payload,
        )
        return ChatMessageResponse.from_orm(msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{room_id}/attachments", response_model=ChatMessageResponse)
async def upload_attachment_message(
    room_id: int,
    file: UploadFile = File(...),
    message_text: str = "",
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment_url = await upload_chat_attachment(file)
    payload = ChatMessageCreate(
        message_text=message_text or file.filename or "",
        message_type="file",
    )
    try:
        msg = ChatService.create_message(
            db=db,
            room_id=room_id,
            sender_id=current_user["sub"],
            payload=payload,
            attachment_url=attachment_url,
            attachment_type=file.content_type,
        )
        return ChatMessageResponse.from_orm(msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{room_id}/read")
def mark_messages_read(
    room_id: int,
    payload: ReadReceiptRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        count = ChatService.mark_read_up_to(
            db=db,
            room_id=room_id,
            user_id=current_user["sub"],
            up_to_message_id=payload.up_to_message_id,
        )
        return {"success": True, "data": {"updated": count}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/messages/{message_id}", response_model=ChatMessageResponse)
def edit_message(
    message_id: int,
    payload: ChatMessageUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        msg = ChatService.edit_message(
            db=db,
            message_id=message_id,
            user_id=current_user["sub"],
            payload=payload,
        )
        return ChatMessageResponse.from_orm(msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/messages/{message_id}", response_model=ChatMessageResponse)
def delete_message(
    message_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        msg = ChatService.delete_message(
            db=db,
            message_id=message_id,
            user_id=current_user["sub"],
        )
        return ChatMessageResponse.from_orm(msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
