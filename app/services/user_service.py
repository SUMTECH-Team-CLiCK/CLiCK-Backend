from sqlalchemy.orm import Session
from app.models.user import User
from sqlalchemy import select

def is_exist_user(device_uuid:str, db: Session) -> bool:
    query = select(User).where(User.device_uuid == device_uuid)
    user = db.execute(query).scalar()
    if user is None:
        return False
    else:
        return True

def create_user(device_uuid:str, db: Session):
    new_user = User(device_uuid=device_uuid)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print(f"created users : {new_user.user_id}")

