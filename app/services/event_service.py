from app.models.event import Event
from sqlalchemy.orm import Session
def create_event(user_id, input_prompt, fixed_prompt, reason, db:Session) -> Event:
    new_event = Event(user_id=user_id,
                      input_prompt=input_prompt,
                      fixed_prompt=fixed_prompt,
                      reason = reason)
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    print(f"created events : {new_event.user_id}")
    return new_event