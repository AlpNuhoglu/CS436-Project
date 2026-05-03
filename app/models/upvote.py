"""
Upvote ORM model.

Bir kullanıcının bir yorumu beğenmesini temsil eder.
Aynı kullanıcı aynı yorumu yalnızca bir kez beğenebilir.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Upvote(Base):
    __tablename__ = "upvotes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "review_id", name="uq_upvote_user_review"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="upvotes")
    review: Mapped["Review"] = relationship("Review", back_populates="upvotes")

    def __repr__(self) -> str:
        return f"<Upvote user_id={self.user_id} review_id={self.review_id}>"
