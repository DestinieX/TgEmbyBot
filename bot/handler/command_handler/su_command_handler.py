import time

from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, ChannelInvalid
from pyrogram.types import Message
from sqlalchemy.orm import Session

from bot import app
from bot.database import engine
from bot.enum.invite_status import InviteStatus
from bot.enum.service_result_type import ServiceResultType
from bot.handler.command_handler import get_anonymous_tgid
from bot.model.user import User
from bot.scheduler import remove_inactivate_job, remove_non_group_user_job, jobs, scheduler
from bot.service import user_service, invite_code_service
from bot.utils.app_utils import AppUtils
from bot.utils.common_utils import CommonUtils
from bot.utils.db_backup_utils import DbBackupUtils
from config import days_threshold, db_docker_mode, db_container_name, db_user, db_password, db_name, db_backup_dir, \
    max_backups, db_host, log_channel_id


# 设置管理员(命令/set_admin tgid)
@app.on_message(filters.command("set_admin"))
async def set_admin(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        if len(msg_command) == 2:
            # 获取对应的用户信息
            tg_user = await client.get_users(int(msg_command[1]))
            add_result = await user_service.add_admin(msg_command[1])
            if add_result:
                await message.reply(
                    f'用户<a href="tg://user?id={msg_command[1]}">{tg_user.first_name}</a>已设置为管理员')
            else:
                await message.reply("用户不存在")
        else:
            await message.reply("命令格式错误，请输入：/set_admin tgid")
    else:
        await message.reply("无管理员权限，请勿操作")


# 移除管理员(命令/remove_admin tgid)
@app.on_message(filters.command("remove_admin"))
async def remove_admin(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        if len(msg_command) == 2:
            # 获取tgid对应的信息
            tg_user = await client.get_users(int(msg_command[1]))
            del_result = await user_service.del_admin(msg_command[1])
            if del_result:
                await message.reply(
                    f'用户<a href="tg://user?id={msg_command[1]}">{tg_user.first_name}</a>管理员已撤销')
            else:
                await message.reply("用户不存在")
        else:
            await message.reply("命令格式错误，请输入：/remove_admin tgid")
    else:
        await message.reply("无管理员权限，请勿操作")


# 设置白名单(/add_whitelist tgid)
@app.on_message(filters.command("add_whitelist"))
async def add_whitelist(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        reply_id = AppUtils.get_reply_id(message=message)
        target_tgid = reply_id
        if target_tgid is None:
            if len(msg_command) == 2:
                target_tgid = msg_command[1]
            else:
                await message.reply("命令格式错误，请输入：/add_whitelist tgid")
                return
        if not await user_service.account_exists(tgid=target_tgid):
            await message.reply('用户未入库，无信息')
            return
        # 添加白名单
        result = await user_service.add_white_list(message, target_tgid)
        if result == ServiceResultType.ADD_WHITELIST:
            # 获取对应的用户信息
            tg_user = await app.get_users(target_tgid)
            await message.reply(
                f'用户<a href="tg://user?id={target_tgid}">{tg_user.first_name}</a>已设置白名单')
        elif result == ServiceResultType.ACCOUNT_NOT_EXIST:
            await message.reply("用户不存在")
        elif result == ServiceResultType.TGID_NOT_EXIST:
            await message.reply(f"未找到对应的用户信息，请检查输入的tgid是否正确")
    else:
        await message.reply("无管理员权限，请勿操作")


# 移除白名单(/remove_whitelist tgid)
@app.on_message(filters.command("remove_whitelist"))
async def remove_whitelist(client, message: Message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        reply_id = AppUtils.get_reply_id(message=message)
        target_tgid = reply_id
        if target_tgid is None:
            if len(msg_command) == 2:
                target_tgid = msg_command[1]
            else:
                await message.reply("命令格式错误，请输入：/remove_whitelist tgid")
                return
        if not await user_service.account_exists(tgid=target_tgid):
            await message.reply('用户未入库，无信息')
            return
        result = await user_service.del_white_list(message, target_tgid)
        if result == ServiceResultType.CANCEL_WHITELIST:
            # 获取对应的用户信息
            tg_user = await app.get_users(target_tgid)
            await message.reply(
                f'用户<a href="tg://user?id={target_tgid}">{tg_user.first_name}</a>白名单已取消')
        elif result == ServiceResultType.ACCOUNT_NOT_EXIST:
            await message.reply("用户不存在")
        elif result == ServiceResultType.TGID_NOT_EXIST:
            await message.reply(f"未找到对应的用户信息，请检查输入的tgid是否正确")
    else:
        await message.reply("无管理员权限，请勿操作")


# 注销所有未使用的激活码
@app.on_message(filters.command('expire_all_code'))
async def expire_all_invite_code(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    msg_command = message.command
    if CommonUtils.is_super_admin(tgid):
        await invite_code_service.expire_all_invite_code()
        await message.reply('已注销所有未使用的激活码')
    else:
        await message.reply('请勿随意使用管理员命令')


# 启动自动删除不活跃用户定时任务(/start_inactive_del_job 小时:分钟)
@app.on_message(filters.command("start_inactive_del_job"))
async def start_inactive_user_deletion_job(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        if len(msg_command) == 2 and CommonUtils.is_valid_hour(msg_command[1]):
            # 获得小时和分钟数
            time_parts = msg_command[1].split(":")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            remove_inactivate_job.set_time(hour, minute)
            remove_inactivate_job.execute()
            now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await message.reply(
                f"自动删除超过{days_threshold}天不活跃用户定时任务：已启动\n已设置触发时间：本日{msg_command[1]}\n当前服务器时间为{now} {CommonUtils.get_timezone()}")
        else:
            await message.reply("命令格式错误")
    else:
        await message.reply("无管理员权限，请勿操作")


# 停止自动删除不活跃用户定时任务(/stop_inactive_del_job)
@app.on_message(filters.command("stop_inactive_del_job"))
async def stop_inactive_user_deletion_job(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        remove_inactivate_job.cancel()
        await message.reply(f"自动删除超过{days_threshold}天不活跃用户定时任务：已停止")
    else:
        await message.reply("无管理员权限，请勿操作")


# 启动自动删除不在群组用户(/start_non_group_users_deletion_job 小时:分钟)
@app.on_message(filters.command("start_non_group_del_job"))
async def start_auto_remove_non_group_users_job(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        if len(msg_command) == 2 and CommonUtils.is_valid_hour(msg_command[1]):
            # 获得小时和分钟数
            time_parts = msg_command[1].split(":")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            # 如果存在旧任务，则先取消旧任务
            remove_non_group_user_job.set_time(hour, minute)
            remove_non_group_user_job.execute()
            now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await message.reply(
                f"自动删除不在群组用户定时任务：已启动\n已设置触发时间：本日{msg_command[1]}\n当前服务器时间为{now} {CommonUtils.get_timezone()}")
        else:
            await message.reply("命令格式错误")
    else:
        await message.reply("无管理员权限，请勿操作")


# 停止自动删除不在群组用户(/start_non_group_users_deletion_job 小时:分钟)
@app.on_message(filters.command("stop_non_group_del_job"))
async def stop_auto_remove_non_group_users_job(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        remove_non_group_user_job.cancel()
        await message.reply("自动删除不在群组用户定时任务：已停止")
    else:
        await message.reply("无管理员权限，请勿操作")


# 查看定时任务状态
@app.on_message(filters.command("job_status"))
async def check_job_status(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        if len(jobs) == 0:
            await message.reply("没有正在运行的定时任务")
        for job_name in jobs.keys():
            if job_name in jobs:
                job_instance = scheduler.get_job(jobs[job_name])
                next_run_time = job_instance.next_run_time
                now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
                await message.reply(
                    f"定时任务 <code>{job_name}</code> 正在运行\n下次触发时间: {next_run_time}\n当前服务器时间为{now} {CommonUtils.get_timezone()}")


# bot数据库手动备份
@app.on_message(filters.command("manual_backup"))
async def db_manual_backup(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid) and CommonUtils.is_super_admin(tgid):
        await message.reply('BOT数据库手动备份开始')
        backup_file = None
        if db_docker_mode:
            backup_file = await DbBackupUtils.backup_mysql_db_docker(
                container_name=db_container_name,
                user=db_user,
                password=db_password,
                database_name=db_name,
                backup_dir=db_backup_dir,
                max_backup_count=max_backups
            )
        else:
            backup_file = await DbBackupUtils.backup_mysql_db(
                host=db_host,
                user=db_user,
                password=db_password,
                database_name=db_name,
                backup_dir=db_backup_dir,
                max_backup_count=max_backups
            )
        if backup_file is not None:
            try:
                await app.send_document(
                    chat_id=log_channel_id,
                    document=backup_file,
                    caption=f'BOT数据库备份完毕'
                )
            except (PeerIdInvalid, ChannelInvalid):
                await message.reply('log_channel_id未配置/配置错误，文件仅保存在本地')
            await message.reply('BOT数据库手动备份完毕')
        else:
            try:
                await app.send_message(chat_id=log_channel_id, text="BOT数据库备份失败，请尽快检查相关配置")
            finally:
                await message.reply('BOT数据库手动备份失败，请尽快检查相关配置')
