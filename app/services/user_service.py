from sqlalchemy.orm import Session
from app.models.user import User


def is_exist_user(user_id:str, db: Session) -> bool:
    user = db.get(User, user_id)
    if user is None:
        return False
    else:
        return True

def create_user(user_id:str, db: Session):
    new_user = User(user_id=user_id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print(f"created users : {new_user.user_id}")

