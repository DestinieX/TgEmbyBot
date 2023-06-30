import logging
from datetime import datetime

from pyrogram import filters
from pyrogram.errors import PeerIdInvalid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot import app
from bot.client.emby_client import EmbyClient
from bot.database import engine
from bot.enum.invite_status import InviteStatus
from bot.enum.service_result_type import ServiceResultType
from bot.handler.command_handler import get_anonymous_tgid
from bot.log import logger
from bot.model.config import Config
from bot.model.user import User
from bot.service import invite_code_service, user_service, config_service
from bot.utils.app_utils import AppUtils
from bot.utils.common_utils import CommonUtils
from config import *


# 兑换邀请码(/invite)
@app.on_message(filters.command("invite"))
async def invite(client, message):
    if AppUtils.is_private_chat(message=message):
        tgid = message.from_user.id
        if await AppUtils.is_user_in_group(app, groupid, tgid):
            # 判断传入消息格式
            msg_command = message.command
            if len(msg_command) != 2:
                await message.reply("命令格式错误,请输入/invite 邀请码")
                return
            result = await invite_code_service.redeem_invite_code(tgid=tgid, message=msg_command[1])
            await message.reply(result.value)
            if result == InviteStatus.REGISTRATION_GRANTED:
                tg_user = await app.get_users(tgid)
                logger.info(
                    f"成功：邀请码兑换 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},code={msg_command[1]})")
        else:
            await message.reply("当前用户不在群组内")
    else:
        await message.reply('请勿在群组使用该命令')


# 新建账号
@app.on_message(filters.command("create"))
async def create_account(client, message):
    if AppUtils.is_private_chat(message=message):
        tgid = message.from_user.id
        msg_command = message.command
        if await AppUtils.is_user_in_group(app, groupid, tgid):
            if len(msg_command) == 2:
                config = await config_service.get_config()
                if config is None:
                    await message.reply('配置读取失败，请联系管理员')
                    return
                register_method = config.register_method
                if register_method == 'None':
                    re = await user_service.create(tgid=tgid, message=msg_command[1])
                elif register_method == 'User':
                    re = await user_service.create_user(tgid=tgid, message=msg_command[1])
                elif register_method == 'Time':
                    re = await user_service.create_time(tgid=tgid, message=msg_command[1])
                if re == ServiceResultType.ACCOUNT_EXIST:
                    await message.reply('您已经注册过emby账号，请勿重复注册')
                elif re == ServiceResultType.NOT_ELIGIBLE_FOR_REGISTRATION:
                    await message.reply('您还未获得注册资格')
                elif re == ServiceResultType.EMBY_USERNAME_EXIST:
                    await message.reply('该用户名已被使用')
                else:
                    await message.reply(
                        f'创建成功，账号<code>{re[0]}</code>，初始密码为<code>{re[1]}</code>，密码不进行保存，请尽快登陆修改密码')
            else:
                await message.reply('命令格式错误，请输入/create 用户名')
        else:
            await message.reply('当前用户不在群组内')
    else:
        await message.reply('请勿在群组使用该命令')


# 重置用户密码
@app.on_message(filters.command("reset"))
async def reset_password(client, message):
    if AppUtils.is_private_chat(message):
        tgid = message.from_user.id
        if await user_service.account_exists(tgid):
            if await user_service.reset_user_password(tgid):
                await message.reply('密码已重置为空，请尽快登录修改密码')
            else:
                await message.reply('密码重置失败')
        else:
            await message.reply('用户未入库，无信息')
    else:
        await message.reply('请勿在群组使用该命令')


# 获取用户信息(/info)
@app.on_message(filters.command("info"))
async def get_user_info(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    reply_id = AppUtils.get_reply_id(message=message)
    target_id = reply_id
    if reply_id is None:
        target_id = tgid
    if reply_id is not None and not await user_service.is_admin(tgid=tgid):
        await message.reply('非管理员请勿随意查看他人信息')
        return
    result = await user_service.user_info(tgid=target_id)
    if result[0] == ServiceResultType.NOT_IN_DATABASE:
        await message.reply('用户未入库，无信息')
    elif result[0] == ServiceResultType.ACCOUNT_NOT_EXIST:
        await message.reply(f'此用户没有emby账号，可注册：{result[1]}')
    elif result[0] == ServiceResultType.EMBY_NOT_EXIST:
        await message.reply('用户Emby账号不存在/异常，请联系管理员')
    elif result[0] == ServiceResultType.ACCOUNT_EXIST:
        # reply_id为空且在群组 或者 reply_id不为空 回复信息
        if reply_id is not None or (reply_id is None and not AppUtils.is_private_chat(message)):
            await message.reply('用户信息已私发，请查看')
        await app.send_message(chat_id=tgid,
                               text=f'用户<a href="tg://user?id={target_id}">{target_id}</a>的信息\n'
                                    f'Emby Name: {result[1]}\n'
                                    f'Emby ID: {result[2]}\n'
                                    f'上次活动时间{result[3]}\n'
                                    f'上次登录时间{result[4]}\n'
                                    f'账号创建时间{result[5]}\n'
                                    f'被ban时间{result[6]}\n'
                                    f'是否为白名单用户:{"是" if result[7] else "否"}')


# 获取线路信息(/line)
@app.on_message(filters.command("line"))
async def get_lines(client, message):
    if AppUtils.is_private_chat(message=message):
        tgid = message.from_user.id
        if await user_service.account_exists(tgid=tgid):
            await message.reply(line)
        else:
            await message.reply('无Emby账号无法查看线路')
    else:
        await message.reply('请勿在群组中使用此命令')


# 数量统计(/count)
@app.on_message(filters.command("count"))
async def get_items_count(client, message):
    result = await EmbyClient.items_count()
    await message.reply(f'🎬电影数量：{result[0]}\n📽️剧集数量：{result[1]}\n🎞️总集数：{result[2]}')


# 获取用户tgid(命令/get_tgid @username)
@app.on_message(filters.command("get_tgid"))
async def get_tgid(client, message):
    reply_id = AppUtils.get_reply_id(message)
    if reply_id is None:
        if await AppUtils.is_anonymous_admin(message):
            await message.reply('匿名管理员无法在群组使用该功能')
            return
        tgid = message.from_user.id
        if len(message.command) == 1:
            await message.reply(f"当前用户的tgid为<code>{tgid}</code>")
            return

        # 获取命令中的参数
        if len(message.command) != 2:
            await message.reply("使用方法：/get_tgid @username")
            return

        # 提取参数中的用户名
        username = message.command[1]
        if not username.startswith("@"):
            await message.reply("使用方法：/get_tgid @username")
            return
        username = username[1:]

        # 获取用户信息
        user = await app.get_users(username)
        if user is None:
            await message.reply(f"找不到用户名为 {username} 的用户")
            return
        # 返回用户的TGID
        await message.reply(f"{user.first_name} 的TGID为 {user.id}")
    else:
        user = await app.get_users(reply_id)
        await message.reply(f"{user.first_name} 的TGID为 {user.id}")


# 通过tgid获取用户信息
@app.on_message(filters.command("get_tginfo"))
async def get_tg_info_by_tgid(client, message):
    # 获取命令中的参数
    if len(message.command) != 2:
        await message.reply("使用方法：/get_tginfo tgid")
        return
    # 输入的tgid
    input_tgid = message.command[1]
    try:
        tg_user = await app.get_users(input_tgid)
        await message.reply(
            f'tgid={input_tgid}的用户为 <a href="tg://user?id={input_tgid}">{tg_user.first_name}</a>')
    except PeerIdInvalid:
        await message.reply(f'tgid = {input_tgid} 的用户未找到')


# 查看当前服务器注册人数及可注册人数/截止时间(/reg_info)
@app.on_message(filters.command("reg_info"))
async def server_info(client, message):
    async with AsyncSession(engine) as session:
        count = await user_service.get_reg_count()
        result = await session.execute(select(Config).where(Config.id == 1))
        bot_config = result.scalar_one_or_none()
        if bot_config is None:
            await message.reply("bot配置错误，请联系管理员")
            return
        # register_public_user = bot_config.register_public_user
        register_public_user = user_service.registration_queue.qsize()
        register_public_time = bot_config.register_public_time
        register_method = "邀请码注册" if bot_config.register_method == 'None' else \
            "限制时间注册" if bot_config.register_method == 'Time' else \
                "限制人数注册" if bot_config.register_method == 'User' else ''
        await message.reply(f'当前已注册人数: {count}\n'
                            f'当前使用的注册方式: {register_method}\n'
                            f'当前可注册人数: {register_public_user}\n'
                            f'当前注册截止时间: {register_public_time.strftime("%Y-%m-%d %H:%M:%S")} {CommonUtils.get_timezone()}')
