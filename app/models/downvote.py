"""
Downvote ORM model.

Bir kullanıcının bir yorumu faydasız bulmasını temsil eder.
Aynı kullanıcı aynı yorumu yalnızca bir kez faydasız olarak işaretleyebilir.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Downvote(Base):
    __tablename__ = "downvotes"

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
        UniqueConstraint("user_id", "review_id", name="uq_downvote_user_review"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="downvotes")
    review: Mapped["Review"] = relationship("Review", back_populates="downvotes")

    def __repr__(self) -> str:
        return f"<Downvote user_id={self.user_id} review_id={self.review_id}>"
