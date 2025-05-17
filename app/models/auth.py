from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from app.db.database import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)  # "meituan" 或 "duowei"
    status = Column(String(20), nullable=False)  # "active", "expired", "failed"
    cookies = Column(Text)  # JSON格式的cookies
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used = Column(DateTime)
