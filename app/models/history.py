from sqlalchemy import Index, DateTime, Column, Integer, String, ForeignKey
from app.db.session import Base
from sqlalchemy.sql import func,desc
from sqlalchemy.orm import relationship



class History(Base):
    __tablename__ = 'histories'
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    topic = Column(String(40), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="histories")

    __table_args__ = (
        Index("ix_hist_user_created", "user_id", desc("created_at")),
        # 3) (선택) 같은 유저가 같은 토픽을 중복 저장 못 하게 하려면 활성화
        # UniqueConstraint("user_id", "topic", name="uq_hist_user_topic"),
    )