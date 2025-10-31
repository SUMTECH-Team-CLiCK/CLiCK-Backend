from app.models.event import Event
from app.models.user import User
from sqlalchemy.orm import Session
from app.services import user_service
from fastapi import HTTPException
from sqlalchemy import select


def create_event(device_uuid:str, input_prompt, result, db:Session) -> Event:
    user = db.execute(
        select(User).where(User.device_uuid == device_uuid)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 device_uuid")

    # tag_list = [p.tag for p in getattr(result, "patches", [])]
    # tags_distinct_list = list(dict.fromkeys(tag_list))
    patches = result.get("patches", [])
    tags = [p["tag"] for p in patches if "tag" in p]
    new_event = Event(user_id=user.user_id,
                      input_prompt=input_prompt,
                      fixed_prompt=result["full_suggestion"],
                      reason = ''.join(tags))
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    print(f"created events : {new_event.user_id}")
    return new_event