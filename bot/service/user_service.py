import asyncio
import datetime
import json
import logging
import random
import string
import time

import requests
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot import app
from bot.client.emby_client import EmbyClient
from bot.database import engine
from bot.enum.service_result_type import ServiceResultType
from bot.log import logger
from bot.model.config import Config
from bot.model.user import User
from bot.service import registration_queue, media_library_service
from bot.utils.common_utils import CommonUtils
from config import admin_list, embyurl, embyapi, is_create_by_copy, prototype_account_id


# 获取已注册用户数量
async def get_reg_count():
    async with AsyncSession(engine) as session:
        result = await session.execute(select(func.count()).where(User.emby_id.is_not(None)))
        return result.scalar()


# 是否可注册
async def can_register(tgid=0):
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(User)
            .where(User.tgid == tgid)
            .where(User.is_reg_allowed.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        return True


# 是否存在emby账号
async def account_exists(tgid=0):
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(User)
            .where(User.tgid == tgid)
            .where(User.emby_name.is_not(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        return True


async def is_admin(tgid=0):
    # 判断当前用户的tgid是否在配置文件中
    for i in range(0, len(admin_list)):
        if tgid == admin_list[i]:
            return True
    # 判断用户在db里是否标记为管理员
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(User)
            .where(User.tgid == tgid)
            .where(User.is_admin.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        return True


# 设置开放注册限制人数(Queue)
async def set_open_reg_slots(num_slots):
    if int(num_slots) == 0:
        await clear_queue(registration_queue)
    for _ in range(int(num_slots)):
        await registration_queue.put(True)
    return int(num_slots)


# 清空asyncio队列
async def clear_queue(queue):
    while not queue.empty():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            return


# 重置用户密码
async def reset_user_password(tgid):
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid))
        user = result.scalar_one_or_none()
        return await EmbyClient.reset_password(user.emby_id)


# 添加管理员
async def add_admin(tgid):
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid))
        user = result.scalar_one_or_none()  # type: User
        if user is None:
            return False
        user.is_admin = True
        await session.commit()
        return True


# 移除管理员
async def del_admin(tgid):
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid))
        user = result.scalar_one_or_none()
        if user is None:
            return False
        user.is_admin = False
        await session.commit()
        return True


# 获取用户信息
async def user_info(tgid=0):
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid))
        user = result.scalar_one_or_none()
        if user is None:
            return ServiceResultType.NOT_IN_DATABASE, None
        emby_name = user.emby_name
        emby_id = user.emby_id
        is_reg_allowed = user.is_reg_allowed
        ban_time = user.ban_time
        is_in_whitelist = user.is_in_whitelist
        if emby_id is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST, is_reg_allowed
        if ban_time is None:
            ban_time = 'None'
        else:
            expired = time.localtime(ban_time)
            expired = time.strftime("%Y/%m/%d %H:%M:%S", expired)  # change the time format
            ban_time = expired
        try:
            r = await EmbyClient.get_user_info(emby_id)
        except json.decoder.JSONDecodeError:
            return ServiceResultType.EMBY_NOT_EXIST, None
        last_act_time = CommonUtils.local_time(time=r.get('LastActivityDate', None))
        created_time = CommonUtils.local_time(time=r.get('DateCreated', None))
        last_login_date = CommonUtils.local_time(time=r.get('LastLoginDate', None))
        return ServiceResultType.ACCOUNT_EXIST, emby_name, emby_id, last_act_time, last_login_date, created_time, ban_time, is_in_whitelist


# 根据注册资格注册账号(邀请码)
async def create(tgid=0, message=''):  # register with invite code
    async with AsyncSession(engine) as session:
        # 有可能没有账号，数据库也未记录
        if await account_exists(tgid=tgid):
            return ServiceResultType.ACCOUNT_EXIST  # already have an account
        # 数据库有记录，且可注册，则进行
        if not await can_register(tgid=tgid):
            return ServiceResultType.NOT_ELIGIBLE_FOR_REGISTRATION  # cannot register
        name = message
        try:
            emby_response = await EmbyClient.create_user(username=name, is_copy_create=is_create_by_copy)
        except json.decoder.JSONDecodeError:
            logger.error(f"失败：注册账号(邀请码注册) 用户(tgid='{tgid}',emby_name={name},message={emby_response})")
            if emby_response.find('already exists.'):
                return ServiceResultType.EMBY_USERNAME_EXIST  # already exists
        if not is_create_by_copy:
            await EmbyClient.edit_policy(emby_id=emby_response['Id'])
        # 如果开启了禁用媒体库功能，则更新policy
        await media_library_service.update_user_libs_policy(emby_id=emby_response['Id'])
        new_password = ''.join(random.sample(string.ascii_letters + string.digits, 8))
        await EmbyClient.change_password(emby_id=emby_response['Id'], old_password='', new_password=new_password)
        result = await session.execute(select(User).where(User.tgid == tgid))
        user = result.scalar_one_or_none()  # type: User
        user.emby_name = emby_response['Name']
        user.is_reg_allowed = False
        user.emby_id = emby_response['Id']
        await session.commit()
        tg_user = await app.get_users(tgid)
        logger.info(
            f"成功：注册账号(邀请码注册) 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={name},emby_id={emby_response['Id']})")
        return emby_response['Name'], new_password


# 根据时间开启注册
async def create_time(tgid=0, message=''):
    async with AsyncSession(engine) as session:
        result = await session.execute(select(Config).where(Config.id == 1))
        config = result.scalar_one_or_none()
        register_public_time = config.register_public_time
        if datetime.datetime.now() >= register_public_time:
            config.register_method = 'None'
            await session.commit()
            return ServiceResultType.NOT_ELIGIBLE_FOR_REGISTRATION
        else:
            if await account_exists(tgid=tgid):
                return ServiceResultType.ACCOUNT_EXIST  # already have an account
            name = message
            try:
                emby_response = await EmbyClient.create_user(username=name, is_copy_create=is_create_by_copy)
            except json.decoder.JSONDecodeError:
                logger.error(
                    f"失败：注册账号(邀请码注册) 用户(tgid='{tgid}',emby_name={name},message={emby_response})")
                if emby_response.find('already exists.'):
                    return ServiceResultType.EMBY_USERNAME_EXIST  # already exists
            if not is_create_by_copy:
                await EmbyClient.edit_policy(emby_id=emby_response['Id'])
            # 如果开启了禁用媒体库功能，则更新policy
            await media_library_service.update_user_libs_policy(emby_id=emby_response['Id'])
            new_password = ''.join(random.sample(string.ascii_letters + string.digits, 8))
            await EmbyClient.change_password(emby_id=emby_response['Id'], old_password='', new_password=new_password)
            # 根据tgid获取user
            result = await session.execute(select(User).where(User.tgid == tgid))
            user = result.scalar_one_or_none()  # type: User
            # 判断user是否存在，若存在则修改，不存在则新增
            if user is None:
                user = User(tgid=tgid, emby_name=emby_response['Name'], emby_id=emby_response['Id'])
                session.add(user)
            else:
                user.emby_name = emby_response['Name']
                user.is_reg_allowed = False
                user.emby_id = emby_response['Id']
            await session.commit()
            tg_user = await app.get_users(tgid)
            logger.info(
                f"成功：注册账号(限制时间注册) 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={name},emby_id={emby_response['Id']})")
            return emby_response['Name'], new_password


# 限制人数开启注册
async def create_user(tgid=0, message=''):
    async with AsyncSession(engine) as session:
        try:
            if await account_exists(tgid=tgid):
                return ServiceResultType.ACCOUNT_EXIST  # already have an account
            registration_queue.get_nowait()
            name = message
            try:
                emby_response = await EmbyClient.create_user(username=name,
                                                             is_copy_create=is_create_by_copy)  # create a new user
            except json.decoder.JSONDecodeError:
                logger.error(
                    f"失败：注册账号(邀请码注册) 用户(tgid='{tgid}',emby_name={name},message={emby_response})")
                if emby_response.find('already exists.'):
                    return ServiceResultType.EMBY_USERNAME_EXIST  # already exists
            if not is_create_by_copy:
                await EmbyClient.edit_policy(emby_id=emby_response['Id'])
            # 如果开启了禁用媒体库功能，则更新policy
            await media_library_service.update_user_libs_policy(emby_id=emby_response['Id'])
            new_password = ''.join(random.sample(string.ascii_letters + string.digits, 8))
            await EmbyClient.change_password(emby_id=emby_response['Id'], old_password='', new_password=new_password)
            # 根据tgid获取user
            result = await session.execute(select(User).where(User.tgid == tgid))
            user = result.scalar_one_or_none()  # type: User
            # 判断user是否存在，若存在则修改，不存在则新增
            if user is None:
                user = User(tgid=tgid, emby_name=emby_response['Name'], emby_id=emby_response['Id'])
                session.add(user)
            else:
                user.emby_name = emby_response['Name']
                user.is_reg_allowed = False
                user.emby_id = emby_response['Id']
            # config.register_public_user -= 1
            await session.commit()
            tg_user = await app.get_users(tgid)
            logger.info(
                f"成功：注册账号(限制人数注册) 用户(tgid='{tgid},username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},'emby_name={name},emby_id={emby_response['Id']})")
            return emby_response['Name'], new_password
        except asyncio.QueueEmpty:
            result = await session.execute(select(Config).where(Config.id == 1))
            config = result.scalar_one_or_none()
            config.register_method = 'None'
            await session.commit()
            return ServiceResultType.NOT_ELIGIBLE_FOR_REGISTRATION


# 禁用emby账号
async def ban_emby(message='', replyid=0):
    async with AsyncSession(engine) as session:
        if await account_exists(tgid=replyid):
            result = await session.execute(
                select(User)
                .where(User.tgid == replyid)
                .where(User.emby_name.isnot(None))
            )
            user = result.scalar_one_or_none()
            emby_name = user.emby_name
            emby_id = user.emby_id
            policy_dict = await EmbyClient.get_policy_dict(emby_id)
            policy_dict['IsDisabled'] = 'true'
            policy = json.dumps(policy_dict)
            await EmbyClient.edit_policy(emby_id, policy)
            user.ban_time = datetime.datetime.now()
            await session.commit()
            return ServiceResultType.EMBY_BAN, emby_name  # Ban the user's emby account
        else:
            if await can_register(tgid=replyid):
                result = await session.execute(select(User).where(User.tgid == replyid))
                user = result.scalar_one_or_none()  # type: User
                user.is_reg_allowed = False
                await session.commit()
                return ServiceResultType.REGISTRATION_RESTRICTED, 'CannotReg'  # set cannot register
            else:
                return ServiceResultType.DO_NOTHING, 'DoNothing'  # do nothing


# 解禁emby账号
async def unban_emby(message='', replyid=0):
    async with AsyncSession(engine) as session:
        if await account_exists(tgid=replyid):
            result = await session.execute(
                select(User)
                .where(User.tgid == replyid)
                .where(User.emby_name.isnot(None))
            )
            user = result.scalar_one_or_none()
            emby_name = user.emby_name
            emby_id = user.emby_id
            policy_dict = await EmbyClient.get_policy_dict(emby_id)
            policy_dict['IsDisabled'] = 'false'
            policy = json.dumps(policy_dict)
            await EmbyClient.edit_policy(emby_id, policy)
            user.ban_time = None
            await session.commit()
            return ServiceResultType.EMBY_UNBAN, emby_name  # Unban the user's emby account
        else:
            return ServiceResultType.DO_NOTHING, 'DoNothing'  # do nothing


# 删除用户
async def delete_user_account(message, tgid, tg_user):
    username = tg_user.first_name
    logger.info(
        f"执行：删除账号(主动删除) 用户(tgid='{tgid}',username={username})")
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid))
        del_user = result.scalar_one_or_none()  # type: User
        emby_username = del_user.emby_name
        emby_id = del_user.emby_id
        # 检查响应状态码
        if await EmbyClient.delete_emby(emby_id):
            logger.info(
                f"成功：删除Emby账号(主动删除) 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={emby_username},emby_id={emby_id})")
        else:
            logger.error(
                f"失败：删除Emby账号(主动删除) 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={emby_username},emby_id={emby_id})")
        # 清除数据库信息
        await session.delete(del_user)
        await session.commit()
        logger.info(
            f"成功：删除DB账号(主动删除) 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={emby_username},emby_id={emby_id})")
        return True


# 添加白名单
async def add_white_list(message, tgid):
    # 获取tgid对应的信息
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(User).where(User.tgid == tgid))
            user = result.scalar_one_or_none()  # type: User
            if user is not None:
                user.is_in_whitelist = True
                await session.commit()
                return ServiceResultType.ADD_WHITELIST
            else:
                return ServiceResultType.ACCOUNT_NOT_EXIST
    except ValueError:
        # 用户不存在，处理异常情况
        return ServiceResultType.TGID_NOT_EXIST


# 删除白名单
async def del_white_list(message, tgid):
    try:

        async with AsyncSession(engine) as session:
            result = await session.execute(select(User).where(User.tgid == tgid))
            user = result.scalar_one_or_none()  # type: User
            if user is not None:
                user.is_in_whitelist = False
                await session.commit()
                return ServiceResultType.CANCEL_WHITELIST
            else:
                return ServiceResultType.ACCOUNT_NOT_EXIST
    except ValueError:
        # 用户不存在，处理异常情况
        return ServiceResultType.TGID_NOT_EXIST
