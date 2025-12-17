from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.chat import ChatRoom, ChatMessage
from app.models.appointment import Appointment
from app.schemas.chat import ChatMessageCreate, ChatMessageUpdate


class ChatService:
    # ---------------- Rooms ----------------

    @staticmethod
    def get_or_create_room_for_appointment(
        db: Session,
        appointment_id: int,
    ) -> ChatRoom:
        room = (
            db.query(ChatRoom)
            .filter(ChatRoom.appointment_id == appointment_id)
            .first()
        )
        if room:
            return room

        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise ValueError("Appointment not found")

        room = ChatRoom(
            appointment_id=appointment_id,
            doctor_id=appt.doctor_id,
            patient_id=appt.patient_id,
            room_type="appointment",
            room_status="active",
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def list_user_rooms(db: Session, user_id: int, skip: int = 0, limit: int = 20) -> List[ChatRoom]:
        return (
            db.query(ChatRoom)
            .filter(
                or_(
                    ChatRoom.doctor_id == user_id,
                    ChatRoom.patient_id == user_id,
                )
            )
            .order_by(ChatRoom.last_message_at.desc().nullslast())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
    # Re-adding helper for direct room lookup/creation without appointment if needed, 
    # but relying on appointment-based flow as primary per user snippet.
    # However, to maintain compatibility with my previous simpler implementation's potential usages:
    @staticmethod
    def create_or_get_room(
        db: Session, doctor_id: int, patient_id: int, appointment_id: Optional[int] = None
    ) -> ChatRoom:
        if appointment_id:
            return ChatService.get_or_create_room_for_appointment(db, appointment_id)
        
        # Fallback for non-appointment logic
        query = db.query(ChatRoom).filter(
            ChatRoom.doctor_id == doctor_id,
            ChatRoom.patient_id == patient_id,
            ChatRoom.room_status == "active",
            ChatRoom.appointment_id == None
        )
        existing_room = query.first()
        if existing_room:
            return existing_room
            
        new_room = ChatRoom(
            doctor_id=doctor_id,
            patient_id=patient_id,
            appointment_id=None,
            room_type="direct",
            last_message_at=datetime.utcnow()
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        return new_room

    @staticmethod
    def get_room_by_id(db: Session, room_id: int) -> Optional[ChatRoom]:
        return db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    # ---------------- Messages ----------------

    @staticmethod
    def create_message(
        db: Session,
        room_id: int,
        sender_id: int,
        payload: ChatMessageCreate,
        attachment_url: Optional[str] = None,
        attachment_type: Optional[str] = None,
    ) -> ChatMessage:
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            raise ValueError("Chat room not found")

        # Basic permission check: sender must be doctor or patient of this room
        if sender_id not in (room.doctor_id, room.patient_id):
            raise ValueError("Not allowed to send messages in this room")

        msg = ChatMessage(
            chat_room_id=room_id,
            sender_id=sender_id,
            message_text=payload.message_text,
            message_type=payload.message_type,
            attachment_url=attachment_url,
            attachment_type=attachment_type,
            replied_to_message_id=payload.replied_to_message_id,
            created_at=datetime.utcnow()
        )
        db.add(msg)

        # Update room preview & unread counts
        room.last_message_at = datetime.utcnow()
        room.last_message_preview = (
            payload.message_text[:200]
            if payload.message_text else "Attachment"
        )

        if sender_id == room.doctor_id:
            room.unread_count_patient += 1
        else:
            room.unread_count_doctor += 1

        db.commit()
        db.refresh(msg)
        return msg
        
    # Alias for compatibility with previous router call
    @staticmethod
    def save_message(
        db: Session,
        room_id: int,
        sender_id: int,
        content: ChatMessageCreate,
        attachment_url: Optional[str] = None,
        attachment_type: Optional[str] = None
    ) -> ChatMessage:
        return ChatService.create_message(
            db, room_id, sender_id, content, attachment_url, attachment_type
        )

    @staticmethod
    def list_messages(
        db: Session,
        room_id: int,
        skip: int = 0,
        limit: int = 50,
        query: Optional[str] = None,
        sender_id: Optional[int] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ) -> Tuple[List[ChatMessage], int]:
        q = db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == room_id,
            ChatMessage.is_deleted == False,  # noqa: E712
        )

        if query:
            q = q.filter(ChatMessage.message_text.ilike(f"%{query}%"))
        if sender_id:
            q = q.filter(ChatMessage.sender_id == sender_id)
        if from_ts:
            q = q.filter(ChatMessage.created_at >= from_ts)
        if to_ts:
            q = q.filter(ChatMessage.created_at <= to_ts)

        total = q.count()
        items = (
            q.order_by(ChatMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total
        
    # Alias for router compatibility
    @staticmethod
    def get_chat_history(
        db: Session, room_id: int, skip: int = 0, limit: int = 50
    ) -> List[ChatMessage]:
        items, _ = ChatService.list_messages(db, room_id, skip, limit)
        return items

    @staticmethod
    def mark_read_up_to(
        db: Session,
        room_id: int,
        user_id: int,
        up_to_message_id: int,
    ) -> int:
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            raise ValueError("Chat room not found")

        # Determine which side is reading
        is_doctor = user_id == room.doctor_id
        is_patient = user_id == room.patient_id
        if not (is_doctor or is_patient):
            raise ValueError("Not allowed in this room")

        q = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.chat_room_id == room_id,
                ChatMessage.id <= up_to_message_id,
                ChatMessage.sender_id != user_id,
                ChatMessage.is_read == False,  # noqa: E712
                ChatMessage.is_deleted == False,  # noqa: E712
            )
        )
        updated = 0
        now = datetime.utcnow()
        # Bulk update is more efficient but manual iteration was requested
        # Converting to list to avoid cursor issues during update if any
        messages = q.all()
        for msg in messages:
            msg.is_read = True
            msg.read_at = now
            updated += 1

        # Reset unread count
        if is_doctor:
            room.unread_count_doctor = 0
        if is_patient:
            room.unread_count_patient = 0

        db.commit()
        return updated
        
    # Alias for compatibility
    @staticmethod
    def mark_messages_as_read(
        db: Session, room_id: int, user_id: int
    ) -> int:
        # We need the last message ID to assume "up_to" or just mark all.
        # The previous implementation marked all unread messages.
        # To reuse the new logic, we'd find the max ID.
        room = db.query(ChatRoom).get(room_id)
        if not room:
            raise ValueError("Room not found")
            
        last_msg = db.query(func.max(ChatMessage.id)).filter(ChatMessage.chat_room_id == room_id).scalar()
        if not last_msg:
            return 0
            
        return ChatService.mark_read_up_to(db, room_id, user_id, last_msg)

    @staticmethod
    def edit_message(
        db: Session,
        message_id: int,
        user_id: int,
        payload: ChatMessageUpdate,
    ) -> ChatMessage:
        msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if not msg:
            raise ValueError("Message not found")
        if msg.sender_id != user_id:
            raise ValueError("You can only edit your own messages")
        if msg.is_deleted:
            raise ValueError("Cannot edit deleted message")

        msg.message_text = payload.message_text
        msg.is_edited = True
        msg.edited_at = datetime.utcnow()
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def delete_message(
        db: Session,
        message_id: int,
        user_id: int,
    ) -> ChatMessage:
        msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if not msg:
            raise ValueError("Message not found")
        if msg.sender_id != user_id:
            raise ValueError("You can only delete your own messages")

        msg.is_deleted = True
        msg.deleted_at = datetime.utcnow()
        # Optionally redact text
        msg.message_text = "[deleted]"
        db.commit()
        db.refresh(msg)
        return msg
