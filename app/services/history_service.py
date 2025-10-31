from app.models.history import History, MessageRole
from sqlalchemy.orm import Session
from app.models.user import User
from typing import List, Sequence
from sqlalchemy import select

def create_history(in_, role:MessageRole, db:Session):
    if role == MessageRole.USER.value:
        query = select(User).where(User.device_uuid == in_.device_uuid)
        user = db.execute(query).scalar()

        new_history = History(
                user_id=user.user_id,
                room_id=in_.room_id,
                role=MessageRole.USER.value,
                topic=in_.input_prompt)
        db.add(new_history)
        db.commit()
        db.refresh(new_history)
        return new_history
    else:
        query = select(User).where(User.device_uuid == in_.device_uuid)
        user = db.execute(query).scalar()

        new_history = History(
            user_id=user.user_id,
            room_id=in_.room_id,
            role=MessageRole.AI,
            topic=in_.input_prompt)
        db.add(new_history)
        db.commit()
        db.refresh(new_history)
        return new_history


def get_histories(device_uuid: str, room_id: str, db: Session):
    query = select(User).where(User.device_uuid == device_uuid)
    user = db.execute(query).scalar()
    query = select(History).where(History.user_id == user.user_id and History.room_id == room_id).order_by(History.created_at.desc()).limit(5)
    histories : Sequence[History] = db.execute(query).scalars().all()
    return histories

def get_histories_new(device_uuid: str, db: Session):
    query = select(User).where(User.device_uuid == device_uuid)
    user = db.execute(query).scalar()
    query = select(History).where(History.user_id == user.user_id).order_by(
        History.created_at.desc()).limit(20)
    histories: Sequence[History] = db.execute(query).scalars().all()
    return histories