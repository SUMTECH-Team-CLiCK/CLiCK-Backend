from datetime import datetime
from sqlalchemy import Column, Integer, TIMESTAMP, String, Boolean
from sqlalchemy.sql import func
from app.db.session import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True) #클라이언트의 uuid
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    # is_active = Column(Boolean, default=False)

    events = relationship("Event", back_populates="user")