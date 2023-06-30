import datetime
from typing import Optional

from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from bot.model import *


# invite code 类
class InviteCode(Base):
    __tablename__ = 'invite_code'
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    tgid: Mapped[int] = mapped_column(BigInteger)
    create_time: Mapped[Optional[datetime.datetime]] = mapped_column(default=None)
    is_used: Mapped[bool] = mapped_column(default=False)
    expire_time: Mapped[Optional[datetime.datetime]] = mapped_column(default=None)
