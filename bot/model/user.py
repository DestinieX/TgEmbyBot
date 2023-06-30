# User类
import datetime
from typing import Optional

from sqlalchemy import Column, BigInteger, CHAR, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.model import *


# class User(Base):
#     __tablename__ = 'user'
#     tgid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
#     admin: Mapped[str] = mapped_column(CHAR(50), default='F')
#     emby_name: Mapped[Optional[str]] = mapped_column(String(50),default=None)
#     emby_id: Mapped[Optional[str]] = mapped_column(String(50),default=None)
#     canrig: Mapped[str] = mapped_column(CHAR(50),default='F')
#     bantime: Mapped[int] = mapped_column(BigInteger)
#     is_in_whitelist: Mapped[int] = mapped_column(Integer)
class User(Base):
    __tablename__ = 'user'
    tgid: Mapped[int] = mapped_column(primary_key=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    emby_name: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    emby_id: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    is_reg_allowed: Mapped[bool] = mapped_column(default=False)
    ban_time: Mapped[Optional[datetime.datetime]] = mapped_column(default=None)
    is_in_whitelist: Mapped[bool] = mapped_column(default=False)
    allowed_libs: Mapped[str] = mapped_column(String(200), default=None)
