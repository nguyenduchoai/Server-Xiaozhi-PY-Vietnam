"""
Usage Tracker Model

Tracks daily/monthly usage statistics for analytics and billing.
"""

from datetime import datetime, timezone, date
from sqlalchemy import String, DateTime, Integer, BigInteger, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class UsageTracker(Base):
    __tablename__ = "usage_tracker"
    
    # Composite primary key: user + date
    __table_args__ = (
        Index("idx_usage_user_date", "user_id", "tracking_date"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # Foreign keys
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False, index=True)
    
    # Tracking period
    tracking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Usage counters
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_llm_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tts_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tts_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_asr_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_webhook_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Resource counts (snapshot at end of day)
    active_agents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_devices: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    knowledge_base_size_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
        default=None
    )
    
    # Relationships
    user = relationship("User", backref="usage_history")
    
    def __repr__(self) -> str:
        return f"<UsageTracker user_id={self.user_id} date={self.tracking_date} tokens={self.total_tokens}>"
