from __future__ import annotations

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, _uuid


class VirtualKeyAssignment(Base):
    __tablename__ = "virtual_key_assignments"
    __table_args__ = (UniqueConstraint("vk_id", "api_key_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vk_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    api_key_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<VirtualKeyAssignment id={self.id!r} vk_id={self.vk_id!r} "
            f"api_key_id={self.api_key_id!r} priority={self.priority!r}>"
        )
