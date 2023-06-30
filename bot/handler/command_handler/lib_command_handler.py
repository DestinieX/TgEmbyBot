from pyrogram import filters

from bot import app
from bot.enum.service_result_type import ServiceResultType
from bot.handler.command_handler import get_anonymous_tgid
from bot.log import logger
from bot.service import user_service, media_library_service
from bot.utils.app_utils import AppUtils
from bot.utils.common_utils import CommonUtils
from config import groupid


# 查看需要权限开启的媒体库(user可用)(/get_restricts)
@app.on_message(filters.command('get_restricts'))
async def get_restricts(client, message):
    if await media_library_service.is_lib_restrict_enabled():
        libs = await media_library_service.get_restriction_libs()
        result = ''
        for item in libs:
            result += f'- {item}\n'
        await message.reply(f'需要权限开启的媒体库为:\n{result}')
    else:
        await message.reply('媒体库限制未开启')


# 开启媒体库限制功能(/enable_lib_restrict 媒体库1 媒体库2...)
@app.on_message(filters.command('enable_lib_restrict'))
async def enable_lib_restrict(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        if len(msg_command) > 1:
            blocked_lib_list = msg_command[1:]
            result = await media_library_service.enable_lib_restrictions(blocked_lib_list)
            if result == ServiceResultType.LIBRARY_NOT_EXIST:
                await message.reply('媒体库不存在，请重新输入')
            elif result == ServiceResultType.SUCCESS:
                await message.reply('媒体库限制已开启，仅对新用户有效。\n'
                                    '若要对所有用户有效，请使用(根据媒体库限制列表关闭所有用户对应媒体库访问)功能')
        else:
            await message.reply('命令格式错误')
    else:
        await message.reply('无管理员权限，请勿操作')


# 关闭媒体库限制功能(/disable_lib_restrict)
@app.on_message(filters.command('disable_lib_restrict'))
async def enable_lib_restrict(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        result = await media_library_service.disable_lib_restrictions()
        if result == ServiceResultType.SUCCESS:
            await message.reply('媒体库限制已关闭')
    else:
        await message.reply('无管理员权限，请勿操作')


# 查看所有媒体库列表(/get_all_libs)
@app.on_message(filters.command('get_all_libs'))
async def get_all_libs(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        result = ''
        for item in await media_library_service.get_emby_libs():
            result += '- ' + item + '\n'
        await message.reply(f'Emby媒体库列表：\n'
                            f'{result}')
    else:
        await message.reply('无管理员权限，请勿操作')


# 查看当前限制的媒体库列表(/get_restrict_libs)
@app.on_message(filters.command('get_restrict_libs'))
async def get_restrict_libs(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        result = ''
        restrict_libs = await media_library_service.get_restriction_libs()
        if CommonUtils.is_not_empty(restrict_libs):
            result = f'限制的媒体库列表：\n'
            for item in restrict_libs:
                result += '- ' + item + '\n'
        else:
            result = '无媒体库限制'
        await message.reply(f'{result}')
    else:
        await message.reply('无管理员权限，请勿操作')


# 根据媒体库限制列表关闭所有用户对应媒体库访问(/update_all_users_libs_policy)
@app.on_message(filters.command('update_all_users_libs_policy'))
async def update_all_users_libs_policy(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        await message.reply('正在更新所有用户的媒体库访问权限\n'
                            '时间较长，请耐心等待(完成后会有提示)')
        result = await media_library_service.update_all_users_libs_policy()
        if result == ServiceResultType.SUCCESS:
            await message.reply('所有用户媒体库访问权限已按限制列表更新')
    else:
        await message.reply('无管理员权限，请勿操作')


# 手动关闭所有用户单一媒体库访问(/disable_all_users_lib 媒体库)
@app.on_message(filters.command('disable_all_users_lib'))
async def disable_all_users_lib(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid=tgid) and CommonUtils.is_super_admin(tgid):
        msg_command = message.command
        if len(msg_command) == 2:
            await message.reply('正在更新所有用户的媒体库访问权限\n'
                                '时间较长，请耐心等待(完成后会有提示)')
            result = await media_library_service.disable_all_users_lib(msg_command[1])
            if result == ServiceResultType.SUCCESS:
                await message.reply('所有用户媒体库访问权限已按限制列表更新')
            elif result == ServiceResultType.LIBRARY_NOT_EXIST:
                await message.reply('媒体库不存在')
        else:
            await message.reply('命令格式错误')
    else:
        await message.reply('无管理员权限，请勿操作')


# 管理员赋予某用户某媒体库权限
# (bot中使用/grant_lib tgid 媒体库)
# (群组内回复/grant_lib 媒体库)
@app.on_message(filters.command('grant_lib'))
async def grant_lib_permission(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid):
        msg_command = message.command
        # reply_id为None时命令分三段 /grant_lib tgid 媒体库
        # reply_id不为None时命令分两段 /grant_lib 媒体库
        if len(msg_command) >= 2:
            try:
                reply_id = AppUtils.get_reply_id(message=message)
                target_tgid = reply_id
                lib_name = msg_command[1]
                if target_tgid is None:
                    if len(msg_command) == 3:
                        target_tgid = msg_command[1]
                        lib_name = msg_command[2]
                    else:
                        await message.reply('命令格式错误')
                        return
                result = await media_library_service.grant_lib_permission(target_tgid, lib_name)
                if result == ServiceResultType.LIBRARY_NOT_EXIST:
                    await message.reply('媒体库不存在')
                elif result == ServiceResultType.ACCOUNT_NOT_EXIST:
                    await message.reply('用户不存在')
                elif result == ServiceResultType.SUCCESS:
                    await message.reply('媒体库权限已授予')
            except ValueError:
                await message.reply('命令格式错误')
        else:
            await message.reply('命令格式错误')
    else:
        await message.reply('请勿随意使用管理员命令')


# 管理员撤销某用户某媒体库权限
# (bot中使用/revoke_lib tgid 媒体库)
# (群组内回复/revoke_lib 媒体库)
@app.on_message(filters.command('revoke_lib'))
async def revoke_lib_permission(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid):
        msg_command = message.command
        # reply_id为None时命令分三段 /grant_lib tgid 媒体库
        # reply_id不为None时命令分两段 /grant_lib 媒体库
        if len(msg_command) >= 2:
            try:
                reply_id = AppUtils.get_reply_id(message=message)
                target_tgid = reply_id
                lib_name = msg_command[1]
                if target_tgid is None:
                    if len(msg_command) == 3:
                        target_tgid = msg_command[1]
                        lib_name = msg_command[2]
                    else:
                        await message.reply('命令格式错误')
                        return
                result = await media_library_service.revoke_lib_permission(target_tgid, lib_name)
                if result == ServiceResultType.LIBRARY_NOT_EXIST:
                    await message.reply('媒体库不存在')
                elif result == ServiceResultType.ACCOUNT_NOT_EXIST:
                    await message.reply('用户不存在')
                elif result == ServiceResultType.SUCCESS:
                    await message.reply('媒体库权限已撤销')
            except ValueError:
                await message.reply('命令格式错误')
        else:
            await message.reply('命令格式错误')
    else:
        await message.reply('请勿随意使用管理员命令')


# 创建媒体库兑换码
# (bot中使用/new_lib_code 数量 媒体库1 媒体库2...)
# (群组内回复/new_lib_code 数量 媒体库1 媒体库2...)
@app.on_message(filters.command("new_lib_code"))
async def new_lib_code(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if await user_service.is_admin(tgid):
        reply_id = AppUtils.get_reply_id(message=message)
        target_tgid = reply_id
        if target_tgid is None:
            target_tgid = tgid
        msg_command = message.command
        # reply_id为None时命令分三段 /new_lib_code 数量 媒体库1 媒体库2...
        # reply_id不为None时命令分三段 /new_lib_code 数量 媒体库1 媒体库2...
        if len(msg_command) > 2:
            try:
                code_count = int(msg_command[1])
                libs = msg_command[2:]
                code_list = await media_library_service.create_libs_codes(tgid, code_count, libs)
                if code_list == ServiceResultType.LIBRARY_NOT_EXIST:
                    await message.reply('媒体库不存在，请重新输入')
                    return
                await message.reply('兑换码生成成功')
                msg = '生成成功，兑换码\n'
                for i in range(code_count):
                    msg += f'<code>{code_list[i]}</code>\n'
                await app.send_message(chat_id=target_tgid, text=msg)
                if reply_id is not None:
                    await app.send_message(chat_id=tgid,
                                           text=f'已为用户<a href="tg://user?id={reply_id}">{reply_id}</a>{msg}')
            except ValueError:
                await message.reply('命令格式错误')
        else:
            await message.reply('命令格式错误')
    else:
        await message.reply('请勿随意使用管理员命令')


# 激活媒体库兑换码(user可用)(/redeem_libs_code 兑换码)
@app.on_message(filters.command("redeem_libs_code"))
async def redeem_libs_code(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if AppUtils.is_private_chat(message=message):
        if await AppUtils.is_user_in_group(app, groupid, tgid):
            # 判断传入消息格式
            msg_command = message.command
            if len(msg_command) != 2:
                await message.reply("命令格式错误,请输入/redeem_libs_code 兑换码")
                return
            result = await media_library_service.redeem_libs_code(tgid, msg_command[1])
            if result == ServiceResultType.ACCOUNT_NOT_EXIST:
                await message.reply('用户不存在')
            elif result == ServiceResultType.LIBRARY_CODE_NOT_EXIST:
                await message.reply('兑换码不存在')
            elif result == ServiceResultType.LIBRARY_CODE_ALREADY_USED:
                await message.reply('兑换码已使用')
            elif result == ServiceResultType.SUCCESS:
                await message.reply('兑换码使用成功，请查询可操作媒体库进行确认')
                tg_user = await app.get_users(tgid)
                logger.info(
                    f"成功：媒体库兑换码兑换成功 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},code={msg_command[1]})")
        else:
            await message.reply("当前用户不在群组内")
    else:
        await message.reply('请勿在群组使用该命令')


# 获取用户可操作媒体库列表(user可用)(/get_authorized_libs)
@app.on_message(filters.command("get_authorized_libs"))
async def get_authorized_libs(client, message):
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
    result = ''
    if not await user_service.account_exists(target_id):
        await message.reply('账号不存在')
        return
    libs = await media_library_service.get_authorized_libs(target_id)
    if CommonUtils.is_not_empty(libs):
        for item in libs:
            result += '- ' + item + '\n'
        # reply_id为空且在群组 或者 reply_id不为空 回复信息
        if reply_id is not None or (reply_id is None and not AppUtils.is_private_chat(message)):
            await message.reply('用户信息已私发，请查看')
        await app.send_message(chat_id=tgid,
                               text=f'用户<a href="tg://user?id={target_id}">{target_id}</a>可操作媒体库列表：\n'
                                    f'{result}')
    else:
        # reply_id为空且在群组 或者 reply_id不为空 回复信息
        if reply_id is not None or (reply_id is None and not AppUtils.is_private_chat(message)):
            await message.reply('用户信息已私发，请查看')
        await app.send_message(chat_id=tgid,
                               text='无可操作的媒体库')


# 获取用户已开启媒体库列表(user可用)(/get_enabled_libs)
@app.on_message(filters.command("get_enabled_libs"))
async def get_enabled_libs(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if AppUtils.is_private_chat(message=message):
        result = ''
        libs = await media_library_service.get_enabled_libs(tgid)
        if CommonUtils.is_not_empty(libs):
            for item in libs:
                result += '- ' + item + '\n'
            await message.reply(f'用户已开启媒体库列表：\n'
                                f'{result}')
        else:
            await message.reply('无开启的媒体库')
    else:
        await message.reply('请勿在群组使用该命令')


# 获取用户已禁用媒体库列表(user可用)(/get_disabled_libs)
@app.on_message(filters.command("get_disabled_libs"))
async def get_disabled_libs(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if AppUtils.is_private_chat(message=message):
        result = ''
        libs = await media_library_service.get_disabled_libs(tgid)
        if CommonUtils.is_not_empty(libs):
            for item in libs:
                result += '- ' + item + '\n'
            await message.reply(f'用户已禁用媒体库列表：\n'
                                f'{result}')
        else:
            await message.reply('无关闭的媒体库')
    else:
        await message.reply('请勿在群组使用该命令')


# 用户启用媒体库(user可用)(/enable_libs 媒体库1 媒体库2...)
@app.on_message(filters.command('enable_libs'))
async def enable_libs(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if AppUtils.is_private_chat(message=message):
        msg_command = message.command
        if len(msg_command) > 1:
            allowed_lib_list = msg_command[1:]
            result = await media_library_service.enable_libs(tgid, allowed_lib_list)
            if result == ServiceResultType.LIBRARY_NOT_EXIST:
                await message.reply('媒体库不存在，请重新输入')
            elif result == ServiceResultType.LIBRARY_RESTRICTED:
                await message.reply('存在无权限开启的媒体库，请重新输入')
            elif result == ServiceResultType.ACCOUNT_NOT_EXIST:
                await message.reply('用户不存在')
            elif result == ServiceResultType.EMBY_SERVICE_ERROR:
                await message.reply('Emby业务执行异常，请联系管理员')
            elif result == ServiceResultType.SUCCESS:
                await message.reply(f'媒体库已启用')
        else:
            await message.reply('命令格式错误')
    else:
        await message.reply('请勿在群组使用该命令')


# 用户关闭媒体库(user可用)(/disable_libs 媒体库1 媒体库2...)
@app.on_message(filters.command('disable_libs'))
async def disable_libs(client, message):
    tgid = await get_anonymous_tgid(client, message)
    if tgid is None:
        tgid = message.from_user.id
    if AppUtils.is_private_chat(message=message):
        msg_command = message.command
        if len(msg_command) > 1:
            blocked_lib_list = msg_command[1:]
            result = await media_library_service.disable_libs(tgid, blocked_lib_list)
            if result == ServiceResultType.LIBRARY_NOT_EXIST:
                await message.reply('媒体库不存在，请重新输入')
            elif result == ServiceResultType.ACCOUNT_NOT_EXIST:
                await message.reply('用户不存在')
            elif result == ServiceResultType.EMBY_SERVICE_ERROR:
                await message.reply('Emby业务执行异常，请联系管理员')
            elif result == ServiceResultType.SUCCESS:
                await message.reply(f'媒体库已关闭')
        else:
            await message.reply('命令格式错误')
    else:
        await message.reply('请勿在群组使用该命令')

