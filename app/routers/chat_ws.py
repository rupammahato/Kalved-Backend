from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user_from_token
from app.services.chat_service import ChatService
from app.services.presence_service import PresenceService
from app.schemas.chat import ChatMessageCreate
from app.models.chat import ChatRoom

router = APIRouter(tags=["chat-ws"])

# room_id -> set of websockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(room_id, set()).add(websocket)

    async def disconnect(self, room_id: int, websocket: WebSocket):
        conns = self.active_connections.get(room_id)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                self.active_connections.pop(room_id, None)

    async def broadcast(self, room_id: int, message: dict):
        for ws in list(self.active_connections.get(room_id, [])):
            await ws.send_json(message)

    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/chat/{room_id}")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(..., description="JWT token"),
    db: Session = Depends(get_db),
):
    # Authenticate
    try:
        current_user = get_current_user_from_token(token, db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = current_user["sub"]

    # Room & permission check
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if user_id not in (room.doctor_id, room.patient_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(room_id, websocket)
    await PresenceService.set_online(user_id)

    try:
        await manager.send_personal(
            websocket,
            {"type": "info", "message": "connected", "room_id": room_id},
        )

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                # keepalive + presence refresh
                await PresenceService.set_online(user_id)
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "message":
                payload = ChatMessageCreate(
                    message_text=data.get("message_text", ""),
                    message_type=data.get("message_type", "text"),
                    replied_to_message_id=data.get("replied_to_message_id"),
                )
                # Persist
                try:
                    msg = ChatService.create_message(
                        db=db,
                        room_id=room_id,
                        sender_id=user_id,
                        payload=payload,
                    )
                except ValueError as e:
                    await manager.send_personal(
                        websocket,
                        {"type": "error", "message": str(e)},
                    )
                    continue

                # Broadcast to all clients in room
                await manager.broadcast(
                    room_id,
                    {
                        "type": "message",
                        "id": msg.id,
                        "room_id": room_id,
                        "sender_id": msg.sender_id,
                        "message_text": msg.message_text,
                        "message_type": msg.message_type,
                        "created_at": msg.created_at.isoformat(),
                        "is_edited": msg.is_edited,
                        "is_deleted": msg.is_deleted,
                        "attachment_url": msg.attachment_url,
                        "attachment_type": msg.attachment_type,
                        "replied_to_message_id": msg.replied_to_message_id,
                    },
                )

            elif msg_type == "read":
                up_to_id = int(data.get("up_to_message_id"))
                try:
                    count = ChatService.mark_read_up_to(
                        db=db,
                        room_id=room_id,
                        user_id=user_id,
                        up_to_message_id=up_to_id,
                    )
                    await manager.broadcast(
                        room_id,
                        {
                            "type": "read_receipt",
                            "user_id": user_id,
                            "up_to_message_id": up_to_id,
                            "updated": count,
                        },
                    )
                except ValueError as e:
                    await manager.send_personal(
                        websocket, {"type": "error", "message": str(e)}
                    )

            else:
                await manager.send_personal(
                    websocket, {"type": "error", "message": "Unsupported message type"}
                )

    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)
        await PresenceService.set_offline(user_id)
    except Exception:
        await manager.disconnect(room_id, websocket)
        await PresenceService.set_offline(user_id)
        await websocket.close()
