import datetime
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot.database import engine
from bot.model.config import Config


# 设置开放注册时间
async def set_open_registration_time(minutes=''):  # public register
    async with AsyncSession(engine) as session:
        result = await session.execute(select(Config).where(Config.id == 1))
        config = result.scalar_one_or_none()
        config.register_public = 'True'
        config.register_public_time = datetime.datetime.now() + timedelta(minutes=float(minutes))
        config.register_method = 'Time'
        await session.commit()
        return datetime.datetime.now() + timedelta(minutes=float(minutes))


# 设置开放注册限制人数(DB)
async def set_open_registration_slots(num=''):
    async with AsyncSession(engine) as session:
        result = await session.execute(select(Config).where(Config.id == 1))
        config = result.scalar_one_or_none()
        config.register_public = 'True'
        config.register_public_user = num
        config.register_method = 'User'
        await session.commit()
        return num


# 获取注册config
async def get_config():
    async with AsyncSession(engine) as session:
        result = await session.execute(select(Config).where(Config.id == 1))
        config = result.scalar_one_or_none()
        return config
