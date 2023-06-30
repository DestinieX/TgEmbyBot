import datetime
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from bot.model import Base


class LibraryCode(Base):
    __tablename__ = 'library_code'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64))
    libs: Mapped[str] = mapped_column(String(200))
    is_used: Mapped[bool] = mapped_column(default=False)
    create_by: Mapped[int]
    used_by: Mapped[int] = mapped_column(default=None)
    create_time: Mapped[Optional[datetime.datetime]] = mapped_column(default=None)
    update_time: Mapped[Optional[datetime.datetime]] = mapped_column(default=None)
