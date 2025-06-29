from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone

from db.database import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)  # "meituan" 或 "duowei"
    status = Column(String(20), nullable=False)  # "active", "expired", "failed"
    cookies = Column(Text)  # JSON格式的cookies
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime)
    last_used = Column(DateTime)
