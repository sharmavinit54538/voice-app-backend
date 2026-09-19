import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    phone_number = Column(String(50), nullable=False, index=True)
    direction = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False, index=True)
    duration = Column(Integer, default=0, nullable=False)
    recording_url = Column(String(1024), nullable=True)
    transcript = Column(Text, nullable=True)
    call_summary = Column(Text, nullable=True)
    analysis = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    lead = relationship("Lead", back_populates="calls")
