import json
import logging
import time
from datetime import datetime

import requests
from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid, ChannelInvalid
from pyrogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot import app
from bot.client.emby_client import EmbyClient
from bot.database import engine
from bot.enum.invite_status import InviteStatus
from bot.enum.playback_rank_type import PlayBackRankType
from bot.enum.service_result_type import ServiceResultType
from bot.log import logger
from bot.model.config import Config
from bot.model.user import User
from bot.scheduler import remove_inactivate_job, jobs, scheduler, remove_non_group_user_job, play_daily_chart_job, \
    play_weekly_chart_job
from bot.service import user_service, registration_queue, invite_code_service, config_service, media_library_service
from bot.utils.app_utils import AppUtils
from bot.utils.common_utils import CommonUtils
from bot.utils.db_backup_utils import DbBackupUtils
from config import *


# 自动删除离开群组成员Emby账号与数据库信息
@app.on_chat_member_updated()
async def on_chat_member_updated(client, chat_member_updated):
    old_chat_member = chat_member_updated.old_chat_member
    new_chat_member = chat_member_updated.new_chat_member
    chat = chat_member_updated.chat
    # 检测成员离开
    if AppUtils.is_user_left_event(old_chat_member, new_chat_member):
        left_member = old_chat_member.user
        tgid = left_member.id
        username = left_member.first_name
        logger.info(
            f"执行：删除账号(成员退群) 用户(tgid='{tgid}',username={username})")
        async with AsyncSession(engine) as session:
            result = await session.execute(select(User).where(User.tgid == tgid))
            del_user = result.scalar_one_or_none()  # type: User
            if del_user is None:
                logger.warning(
                    f"警告：删除账号(成员退群) 该用户并未通过bot注册账号 用户(tgid='{tgid}',username={username})")
                return
            # 删除emby信息
            delete_response = await EmbyClient.delete_emby(del_user.emby_id)
            # 检查响应状态码
            if delete_response:
                logger.info(
                    f"成功：删除Emby账号(成员退群) 用户(tgid='{tgid}',username={username},emby_id={del_user.emby_id})")
            else:
                logger.error(
                    f"失败：删除Emby账号(成员退群) 用户(tgid='{tgid}',username={username},emby_id={del_user.emby_id})")
            # 清除数据库信息
            await session.delete(del_user)
            await client.send_message(groupid, f'<a href="tg://user?id={tgid}">{username}</a> '
                                               f'已离开群组,Emby账号已被删除。')
            logger.info(
                f"成功：删除DB账号(成员退群) 用户(tgid='{tgid}',username={username},emby_id={del_user.emby_id})")
            await session.commit()


# 获取用户命令提示(/start或/help)
@app.on_message(filters.command(["start", "help"]))
async def get_common_commands(client, message):
    if AppUtils.is_private_chat(message):
        await message.reply(
            '用户命令：\n'
            '/invite + 邀请码 使用邀请码获取创建账号资格\n'
            '/create + 用户名 创建用户（用户名不可包含空格）\n'
            '/reset 重置密码为空\n'
            '/info 查看用户信息（仅可查看自己的信息）\n'
            '/line 查看线路\n'
            '/count 查看服务器内片子数量\n'
            '/get_tgid @用户名/群组内回复该用户  获取tgid\n'
            '/get_tginfo +tgid 根据tgid获取用户信息\n'
            '/reg_info 查看当前服务器注册人数及可注册人数/截止时间\n'
            '/help 输出本帮助\n'
            '-\n'
            '管理员命令：\n'
            '/admin 查看管理员命令\n'
            '-\n'
            '超级管理员命令：\n'
            '/su 查看超级管理员命令\n'
            '-\n'
            '定时任务命令：\n'
            '/job 查看定时任务命令\n'
            '-\n'
            '媒体库管理命令：\n'
            '/lib 查看媒体库管理命令\n'
        )
    else:
        await message.reply('请勿在群组使用此命令')


# 获取管理员命令提示(/admin)
@app.on_message(filters.command('admin'))
async def get_admin_commands(client, message):
    tgid = message.from_user.id
    if AppUtils.is_private_chat(message):
        if await user_service.is_admin(tgid):
            await message.reply(
                '管理命令：\n'
                '/new_code 数量 [过期小时数]  [过期小时数]为可选参数\n'
                '/expire_code 激活码 注销单个激活码\n'
                '/register_all_time + 时间（分）开放注册，时长为指定时间\n'
                '/register_all_user + 人数 开放指定数量的注册名额\n'
                '/info 回复一位用户，查看他的信息\n'
                '/ban_emby (不建议使用)禁用一位用户的Emby账号\n'
                '/unban_emby (不建议使用)解禁一位用户的Emby账户\n'
                '/delete_emby + tgid或群组内回复该用户 删除一位用户的emby账号\n'
            )
        else:
            await message.reply('请勿使用管理员命令')


# 获取超级管理员命令提示(/su)
@app.on_message(filters.command('su'))
async def get_su_commands(client, message):
    tgid = message.from_user.id
    if AppUtils.is_private_chat(message):
        if CommonUtils.is_super_admin(tgid):
            await message.reply(
                '超级管理员命令：\n'
                '/set_admin +tgid 设置指定tgid的用户为管理员\n'
                '/remove_admin +tgid移除指定tgid用户的管理员权限\n'
                '/add_whitelist +tgid或群组内回复该用户 设置指定tgid的用户为白名单用户\n'
                '/remove_whitelist +tgid或群组内回复该用户 取消指定tgid的用户白名单身份\n'
                '/expire_all_code 注销所有未使用的激活码\n'
                '/manual_backup 管理员手动备份BOT数据库\n'
            )
        else:
            await message.reply('请勿使用超级管理员命令')


# 获取定时任务命令提示(/job)
@app.on_message(filters.command('job'))
async def get_job_commands(client, message):
    tgid = message.from_user.id
    if AppUtils.is_private_chat(message):
        if CommonUtils.is_super_admin(tgid):
            await message.reply(
                '定时任务命令：\n'
                f'/start_inactive_del_job 小时:分钟 启动"自动删除{days_threshold}天不活跃用户"定时任务，在每天指定的时间运行\n'
                f'/stop_inactive_del_job 停止"自动删除{days_threshold}天不活跃用户"定时任务\n'
                '/start_non_group_del_job 小时:分钟 启动"自动删除不在群组用户"定时任务，在每天指定的时间运行\n'
                '/stop_non_group_del_job 停止"自动删除不在群组用户"定时任务\n'
                '/job_status 获取当前所有定时任务的运行状态\n'
            )
        else:
            await message.reply('请勿使用超级管理员命令')


# 获取媒体库管理命令提示(/lib)
@app.on_message(filters.command('lib'))
async def get_lib_commands(client, message):
    tgid = message.from_user.id
    if AppUtils.is_private_chat(message):
        await message.reply(
            '用户命令:\n'
            '/get_restricts 查看需要权限开启的媒体库\n'
            '/redeem_libs_code 兑换码 兑换媒体库开启权限\n'
            '/get_authorized_libs 获取用户有权限操作的媒体库列表\n'
            '/get_enabled_libs 获取已开启的媒体库列表\n'
            '/get_disabled_libs 获取已关闭的媒体库列表\n'
            '/enable_libs 媒体库1 媒体库2... 开启媒体库\n'
            '/disable_libs 媒体库1 媒体库2... 关闭媒体库\n'
            '-\n'
            '管理员命令:\n'
            '/lib_admin 查看媒体库管理员命令\n'
        )


# 获取媒体库管理命令提示(/lib_admin)
@app.on_message(filters.command('lib_admin'))
async def get_lib_admin_commands(client, message):
    tgid = message.from_user.id
    if AppUtils.is_private_chat(message):
        await message.reply(
            '管理员命令:\n'
            '/new_lib_code 创建媒体库兑换码\n'
            'bot中使用/new_lib_code 数量 媒体库1 媒体库2...\n'
            '群组内回复/new_lib_code 数量 媒体库1 媒体库2...\n'
            '/grant_lib 管理员赋予某用户某媒体库权限\n'
            'bot中使用/grant_lib tgid 媒体库\n'
            '群组内回复/grant_lib 媒体库\n'
            '/revoke_lib 管理员撤销某用户某媒体库权限\n'
            'bot中使用/revoke_lib tgid 媒体库\n'
            '群组内回复/revoke_lib 媒体库\n'
            '-\n'
            '超级管理员命令:\n'
            '/enable_lib_restrict 媒体库1 媒体库2... 开启媒体库限制功能\n'
            '/disable_lib_restrict 关闭媒体库限制功能\n'
            '/get_all_libs 查看所有媒体库列表\n'
            '/get_restrict_libs 查看当前限制的媒体库列表\n'
            '/update_all_users_libs_policy 根据媒体库限制列表关闭所有用户对应媒体库\n'
            '/disable_all_users_lib 媒体库 手动关闭所有用户某媒体库\n'
        )


# @app.on_message(filters.command('test'))
# async def test(client, message):
#     tgid = message.from_user.id
#     if CommonUtils.is_super_admin(tgid):
#         hour = message.command[1]
#         minute = message.command[2]
#         second = message.command[3]
#         # play_daily_chart_job.set_time(hour=hour, minute=minute,second=second)
#         # play_daily_chart_job.execute()
#         play_weekly_chart_job.set_time(day_of_week=None,hour=hour,minute=minute,second=second)
#         play_weekly_chart_job.execute()
#         print('test')
