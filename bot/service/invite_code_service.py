import datetime
import time
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot.database import engine
from bot.enum.invite_status import InviteStatus
from bot.log import logger
from bot.model.invite_code import InviteCode
from bot.model.user import User
from bot.service import user_service
from config import code_prefix


# 生成邀请码
async def create_code(tgid=0, hour=0):
    code = f'{code_prefix}{str(uuid.uuid4())}'
    async with AsyncSession(engine) as session:
        expire_time = None
        if hour != 0:
            expire_time = datetime.datetime.now() + datetime.timedelta(hours=hour)
        invite_code = InviteCode(code=code, tgid=tgid,
                                 create_time=datetime.datetime.now(),
                                 expire_time=expire_time)
        session.add(invite_code)
        await session.commit()
        return code


# 批量生成邀请码
async def create_codes(count=0, tgid=0, hour=0):
    invitecode_list = []
    code_list = []
    expire_time = None
    if hour is not None and hour != 0:
        expire_time = datetime.datetime.now() + datetime.timedelta(hours=hour)
    for i in range(count):
        code_str = f'{code_prefix}{str(uuid.uuid4())}'
        code = InviteCode(code=code_str, tgid=tgid, create_time=datetime.datetime.now(),
                          expire_time=expire_time)
        invitecode_list.append(code)
        code_list.append(code_str)
    async with AsyncSession(engine) as session:
        session.add_all(invitecode_list)
        await session.commit()
        return code_list


# 兑换邀请码
async def redeem_invite_code(tgid=0, message=''):
    async with AsyncSession(engine) as session:
        # 判断当前用户是否可以注册，或者当前用户是否已注册
        result = await session.execute(select(User).where(User.tgid == tgid))
        user = result.scalar_one_or_none()
        if await user_service.can_register(tgid=tgid) or await user_service.account_exists(tgid=tgid):
            return InviteStatus.ALREADY_REGISTERED
        # 从消息获取code
        code = message
        # 从表中查询是否存在该code，且未被使用
        result = await session.execute(
            select(InviteCode)
            .where(InviteCode.code == code)
            .with_for_update()
        )
        invite_code = result.scalar_one_or_none()  # type: InviteCode
        # 若未被使用则进行后续操作
        if invite_code is None:
            return InviteStatus.NOT_FOUND
        if invite_code.is_used:
            return InviteStatus.ALREADY_USED
        # 判断是否过期
        if invite_code.expire_time is not None:
            if datetime.datetime.now() > invite_code.expire_time:
                invite_code.is_used = True
                await session.commit()
                return InviteStatus.CODE_EXPIRED
        # 将code设置为已被使用
        invite_code.is_used = True
        # 将用户的可注册状态设置为T
        if user is None:
            user = User(tgid=tgid, is_reg_allowed=True)
            session.add(user)
        else:
            user.is_reg_allowed = True
        await session.commit()
        return InviteStatus.REGISTRATION_GRANTED


# 注销单个激活码
async def expire_invite_code(code):
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(InviteCode)
            .where(InviteCode.code == code)
            .with_for_update()
        )
        invite_code = result.scalar_one_or_none()  # type: InviteCode
        if invite_code is None:
            return InviteStatus.NOT_FOUND
        if invite_code.is_used:
            return InviteStatus.ALREADY_USED
        invite_code.is_used = True
        await session.commit()
        logger.info(f'成功: 邀请码注销 (code={code})')


# 注销所有未使用激活码
async def expire_all_invite_code():
    async with AsyncSession(engine) as session:
        result = await session.execute(
            update(InviteCode)
            .where(InviteCode.is_used.is_(False))
            .values(is_used=True)
        )
        await session.commit()
