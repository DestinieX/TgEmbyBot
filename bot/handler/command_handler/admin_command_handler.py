import time

from pyrogram import filters, Client
from pyrogram.types import Message

from bot import app
from bot.enum.invite_status import InviteStatus
from bot.enum.service_result_type import ServiceResultType
from bot.handler.command_handler import get_anonymous_tgid
from bot.service import user_service, config_service, invite_code_service
from bot.utils.app_utils import AppUtils
from bot.utils.common_utils import CommonUtils
from config import ban_channel_id, code_default_expire_hour


# 生成注册码(/new_code)
@app.on_message(filters.command("new_code"))
async def new_code(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid):
        reply_id = AppUtils.get_reply_id(message=message)
        target_tgid = reply_id
        if target_tgid is None:
            target_tgid = tgid
        msg_command = message.command
        if len(msg_command) > 1:
            try:
                count = int(msg_command[1])
                if count <= 0:
                    await message.reply('命令格式错误，请输入/new_code 数量 [过期小时数]\n'
                                        '[过期小时数]为可选参数')
                    return
                expire_hour = code_default_expire_hour
                if len(msg_command) == 3:
                    expire_hour = int(msg_command[2])
                if expire_hour < 0:
                    await message.reply('命令格式错误，请输入/new_code 数量 [过期小时数]\n'
                                        '[过期小时数]为可选参数')
                    return
                invite_code_list = await invite_code_service.create_codes(count, tgid, expire_hour)
                await message.reply('邀请码生成成功')
                msg = '生成成功，邀请码:\n'
                for i in range(count):
                    msg += f'<code>{invite_code_list[i]}</code>\n'
                msg += f'过期时间:{" <code>无限制</code>" if expire_hour == 0 else f" <code>{expire_hour}</code> 小时后"}'
                await app.send_message(chat_id=target_tgid, text=msg)
                if reply_id is not None:
                    await app.send_message(chat_id=tgid,
                                           text=f'已为用户<a href="tg://user?id={reply_id}">{reply_id}</a>{msg}')
            except ValueError:
                await message.reply('命令格式错误，请输入/new_code 数量 [过期小时数]\n'
                                    '[过期小时数]为可选参数')
        else:
            await message.reply('命令格式错误，请输入/new_code 数量 [过期小时数]\n'
                                '[过期小时数]为可选参数')
    else:
        await message.reply('请勿随意使用管理员命令')


# 注销单个激活码
@app.on_message(filters.command('expire_code'))
async def expire_invite_code(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    msg_command = message.command
    if await user_service.is_admin(tgid):
        if len(msg_command) == 2:
            code = msg_command[1]
            result = await invite_code_service.expire_invite_code(code)
            if result == InviteStatus.ALREADY_USED:
                await message.reply('邀请码已使用')
                return
            elif result == InviteStatus.NOT_FOUND:
                await message.reply('邀请码不存在')
                return
            await message.reply('邀请码已注销')
        else:
            await message.reply('命令格式错误，请输入/expire_code 邀请码')
    else:
        await message.reply('请勿随意使用管理员命令')


# 设置根据时间开放注册(/register_all_time 时间(分钟))
@app.on_message(filters.command("register_all_time"))
async def open_registration_by_time(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid):
        msg_command = message.command
        if len(msg_command) != 2:
            await message.reply("命令格式错误,请输入/register_all_time 分钟")
            return
        result = await config_service.set_open_registration_time(minutes=msg_command[1])
        expired = result.strftime("%Y-%m-%d %H:%M:%S")
        await message.reply(f"注册已开放，将在{expired} {CommonUtils.get_timezone()}关闭注册")
    else:
        await message.reply('请勿随意使用管理员命令')


# 设置根据人数开放注册(/register_all_user 人数)
@app.on_message(filters.command("register_all_user"))
async def open_registration_by_slots(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid):
        msg_command = message.command
        if len(msg_command) != 2:
            await message.reply("命令格式错误,请输入/register_all_user 人数")
            return
        result = await config_service.set_open_registration_slots(num=0)
        result = await user_service.set_open_reg_slots(msg_command[1])
        await message.reply(f"注册已开放，本次共有{result}个名额")
    else:
        await message.reply('请勿随意使用管理员命令')


# 禁用emby账号(/ban_emby)
@app.on_message(filters.command("ban_emby"))
async def ban_emby_account(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid):
        reply_id = AppUtils.get_reply_id(message=message)
        if reply_id is not None:
            re = await user_service.ban_emby(message=message, replyid=reply_id)
            if re[0] == ServiceResultType.EMBY_BAN:
                await message.reply(f'用户<a href="tg://user?id={reply_id}">{reply_id}</a>的Emby账号{re[1]}已被ban')
                await app.send_message(chat_id=ban_channel_id,
                                       text=f'#Ban\n用户：<a href="tg://user?id={reply_id}">{reply_id}</a>\nEmby账号：{re[1]}\n原因：管理员封禁')
            elif re[0] == ServiceResultType.REGISTRATION_RESTRICTED:
                await message.reply(
                    f'用户<a href="tg://user?id={reply_id}">{reply_id}</a>没有Emby账号，但是已经取消了他的注册资格')
            elif re[0] == ServiceResultType.DO_NOTHING:
                await message.reply(
                    f'用户<a href="tg://user?id={reply_id}">{reply_id}</a>没有Emby账号，也没有注册资格')
        else:
            await message.reply('请回复一条消息使用该功能')
    else:
        await message.reply('请勿随意使用管理员命令')


# 解除emby账号禁用(/ban_emby)
@app.on_message(filters.command("unban_emby"))
async def unban_emby_account(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid):
        reply_id = AppUtils.get_reply_id(message=message)
        if reply_id is not None:
            re = await user_service.unban_emby(message=message, replyid=reply_id)
            if re[0] == ServiceResultType.EMBY_UNBAN:
                await message.reply(
                    f'用户<a href="tg://user?id={reply_id}">{reply_id}</a>的Emby账号{re[1]}已解除封禁')
                await app.send_message(chat_id=ban_channel_id,
                                       text=f'#Unban\n用户：<a href="tg://user?id={reply_id}">{reply_id}</a>\nEmby账号：{re[1]}\n原因：管理员解封')
            elif re[0] == ServiceResultType.DO_NOTHING:
                await message.reply(
                    f'用户<a href="tg://user?id={reply_id}">{reply_id}</a>没有Emby账号，也没有注册资格')

        else:
            await message.reply('请回复一条消息使用该功能')
    else:
        await message.reply('请勿随意使用管理员命令')


# 删除指定Tgid对应的账号与数据库记录(delete_emby)
@app.on_message(filters.command("delete_emby"))
async def delete_account(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid):
        msg_command = message.command
        reply_id = AppUtils.get_reply_id(message=message)
        tg_user = await app.get_users(user_ids=tgid)
        if reply_id is None:
            if len(msg_command) == 2:
                delete_tgid = msg_command[1]
                if not await user_service.account_exists(tgid=delete_tgid):
                    await message.reply('用户未入库，无信息')
                    return
                if await user_service.delete_user_account(message, tgid=delete_tgid, tg_user=tg_user):
                    await message.reply(f'<a href="tg://user?id={tgid}">{tg_user.username}</a> '
                                        f' Emby账号已被删除。')
            else:
                await message.reply('命令格式错误，请输入/delete_account tgid')
        else:
            if not await user_service.account_exists(tgid=reply_id):
                await message.reply('用户未入库，无信息')
                return
            if await user_service.delete_user_account(message, tgid=reply_id, tg_user=tg_user):
                await message.reply(f'<a href="tg://user?id={tgid}">{tg_user.username}</a> '
                                    f' Emby账号已被删除。')
    else:
        await message.reply('请勿随意使用管理员命令')

