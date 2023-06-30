import datetime
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import app
from bot.client.emby_client import EmbyClient
from bot.database import engine
from bot.enum.service_result_type import ServiceResultType
from bot.log import logger
from bot.model.library_code import LibraryCode
from bot.model.user import User
from bot.service import user_service
from bot.utils.common_utils import CommonUtils
from config import lib_code_prefix


# 媒体库限制是否开启
async def is_lib_restrict_enabled():
    if not CommonUtils.get_from_conf('blocked_libs'):
        return False
    return True


# 管理员配置媒体库限制
async def enable_lib_restrictions(blocked_lib_list):
    # 获取emby拥有的所有库名称
    libs_name = await get_emby_libs_name()
    for item in blocked_lib_list:
        if item not in libs_name:
            return ServiceResultType.LIBRARY_NOT_EXIST
    CommonUtils.save_to_conf('blocked_libs', blocked_lib_list)
    return ServiceResultType.SUCCESS


# 管理员关闭媒体库限制
async def disable_lib_restrictions():
    CommonUtils.save_to_conf('blocked_libs', [])
    return ServiceResultType.SUCCESS


# 获取当前限制的媒体库列表
async def get_restriction_libs():
    blocked_lib_list = CommonUtils.get_from_conf('blocked_libs')
    return blocked_lib_list


# 根据限制媒体库信息更新用户访问权限(注册时)
async def update_user_libs_policy(emby_id):
    blocked_lib_list = CommonUtils.get_from_conf('blocked_libs')
    if CommonUtils.is_not_empty(blocked_lib_list):
        policy = await EmbyClient.get_policy_dict(emby_id)
        if not policy:
            logger.error(f'用户policy获取失败(修改所有用户媒体库权限)，emby_id={emby_id}')
        policy['BlockedMediaFolders'] = blocked_lib_list
        policy_json = json.dumps(policy)
        edit_result = await EmbyClient.edit_policy(emby_id, policy_json)
        if not edit_result:
            logger.error(f'用户policy修改失败(修改所有用户媒体库权限)，emby_id={emby_id}')
    return ServiceResultType.SUCCESS


# 根据限制媒体库信息更新所有用户的媒体库访问权限
async def update_all_users_libs_policy():
    blocked_lib_list = CommonUtils.get_from_conf('blocked_libs')
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User.emby_id))
        count = 0
        for emby_id in result.scalars():
            if emby_id is not None:
                count += 1
                policy = await EmbyClient.get_policy_dict(emby_id)
                if not policy:
                    logger.error(f'用户policy获取失败(修改所有用户媒体库权限)，emby_id={emby_id}')
                    continue
                policy['BlockedMediaFolders'] = blocked_lib_list
                policy_json = json.dumps(policy)
                edit_result = await EmbyClient.edit_policy(emby_id, policy_json)
                if not edit_result:
                    logger.error(f'用户policy修改失败(修改所有用户媒体库权限)，emby_id={emby_id}')
                    continue
    return ServiceResultType.SUCCESS


# 手动关闭所有用户某媒体库访问
async def disable_all_users_lib(lib_name):
    emby_libs = await get_emby_libs()
    if lib_name not in emby_libs:
        return ServiceResultType.LIBRARY_NOT_EXIST
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User.emby_id))
        count = 0
        for emby_id in result.scalars():
            if emby_id is not None:
                count += 1
                policy = await EmbyClient.get_policy_dict(emby_id)
                if not policy:
                    logger.error(f'用户policy获取失败(修改所有用户媒体库权限),lib_name={lib_name},emby_id={emby_id}')
                    continue
                user_blocked_list = policy.get('BlockedMediaFolders', [])  # type:list
                if lib_name not in user_blocked_list:
                    user_blocked_list.append(lib_name)
                policy['BlockedMediaFolders'] = user_blocked_list
                policy_json = json.dumps(policy)
                edit_result = await EmbyClient.edit_policy(emby_id, policy_json)
                if not edit_result:
                    logger.error(f'用户policy修改失败(修改所有用户媒体库权限),lib_name={lib_name},emby_id={emby_id}')
                    continue

    return ServiceResultType.SUCCESS


# 管理员赋予用户某媒体库的管理权限
async def grant_lib_permission(tgid, lib_name):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    # 获取emby拥有的所有库名称
    libs_name = await get_emby_libs_name()
    if lib_name not in libs_name:
        return ServiceResultType.LIBRARY_NOT_EXIST
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')  # type:list
        if lib_name not in allowed_libs:
            allowed_libs.append(lib_name)
        if CommonUtils.is_not_empty(allowed_libs):
            user.allowed_libs = ','.join(allowed_libs)
        await session.commit()
    return ServiceResultType.SUCCESS


# 管理员撤销用户某媒体库的管理权限，同时关闭该媒体库的访问权限
async def revoke_lib_permission(tgid, lib_name):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    # 获取emby拥有的所有库名称
    libs_name = await get_emby_libs_name()
    if lib_name not in libs_name:
        return ServiceResultType.LIBRARY_NOT_EXIST
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')  # type:list
        if lib_name in allowed_libs:
            # 关闭媒体库访问权限
            # 获取用户当前policy中禁用列表
            policy = await EmbyClient.get_policy_dict(user.emby_id)
            if not policy:
                logger.error(f'用户policy获取失败(撤销媒体库权限)，emby_id={user.emby_id}')
                return ServiceResultType.EMBY_SERVICE_ERROR
            user_blocked_list = policy.get('BlockedMediaFolders', [])  # type:list
            if lib_name not in user_blocked_list:
                user_blocked_list.append(lib_name)
            # 更新policy
            policy['BlockedMediaFolders'] = user_blocked_list
            edit_result = await EmbyClient.edit_policy(user.emby_id, json.dumps(policy))
            if not edit_result:
                logger.error(f'用户policy修改失败(撤销媒体库权限)，emby_id={user.emby_id}')
                return ServiceResultType.EMBY_SERVICE_ERROR
            # 允许列表中删除该媒体库
            allowed_libs.remove(lib_name)
        if CommonUtils.is_empty(allowed_libs):
            user.allowed_libs = None
        else:
            user.allowed_libs = ','.join(allowed_libs)
        await session.commit()
    return ServiceResultType.SUCCESS


# 获取所有媒体库列表
async def get_emby_libs():
    return await get_emby_libs_name()


# 获取用户已拥有权限的媒体库列表(激活码兑换/管理员授予)
async def get_allowed_list(tgid):
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')
        return allowed_libs


# 获取用户可操作媒体库列表
async def get_authorized_libs(tgid):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    # 获取配置文件中设置的禁止库名称
    blocked_libs = CommonUtils.get_from_conf('blocked_libs')
    if blocked_libs is None:
        blocked_libs = []
    # 获取emby拥有的所有库名称
    libs_name = await get_emby_libs_name()
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')
        # 如果配置文件中的禁止的库在所有库中，则在所有库中删除
        for item in blocked_libs:
            if item in libs_name:
                libs_name.remove(item)
        # 如果用户被特别允许的库不在所有库中，则在所有库中添加
        for item in allowed_libs:
            if item not in libs_name:
                libs_name.append(item)
        return libs_name


# 获取用户无资格操作的媒体库列表
async def get_unauthorized_libs(tgid):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    # 获取配置文件中设置的禁止库名称
    blocked_libs = CommonUtils.get_from_conf('blocked_libs')
    if blocked_libs is None:
        blocked_libs = []
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')
        # 如果禁止列表中存在被允许的库，则删除该库
        for item in allowed_libs:
            if item in blocked_libs:
                blocked_libs.remove(item)
        return blocked_libs


# 获取用户已开启媒体库列表
async def get_enabled_libs(tgid):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        # 清理emby用户policy禁止媒体库中不存在的项
        await cleanup_invalid_lib_emby_policy(user.emby_id)
        # 获取用户当前policy中禁用列表
        policy = await EmbyClient.get_policy_dict(user.emby_id)
        if not policy:
            logger.error(f'用户policy获取失败(获取用户已禁用媒体库列表)，emby_id={user.emby_id}')
            return ServiceResultType.EMBY_SERVICE_ERROR
        user_blocked_list = policy.get('BlockedMediaFolders', [])  # type:list
        emby_libs = await get_emby_libs()
        for item in user_blocked_list:
            if item in emby_libs:
                emby_libs.remove(item)
        return emby_libs


# 获取用户已禁用媒体库列表
async def get_disabled_libs(tgid):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        # 清理emby用户policy禁止媒体库中不存在的项
        await cleanup_invalid_lib_emby_policy(user.emby_id)
        # 获取用户当前policy中禁用列表
        policy = await EmbyClient.get_policy_dict(user.emby_id)
        if not policy:
            logger.error(f'用户policy获取失败(获取用户已禁用媒体库列表)，emby_id={user.emby_id}')
            return ServiceResultType.EMBY_SERVICE_ERROR
        user_blocked_list = policy.get('BlockedMediaFolders', [])  # type:list
        return user_blocked_list


# 启用媒体库
async def enable_libs(tgid, enable_list):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    # 获取配置文件中设置的禁止库名称
    blocked_libs = CommonUtils.get_from_conf('blocked_libs')
    if blocked_libs is None:
        blocked_libs = []
    # 获取emby拥有的所有库名称
    libs_name = await get_emby_libs_name()
    # 判断输入列表的库是否存在
    for item in enable_list:
        if item not in libs_name:
            return ServiceResultType.LIBRARY_NOT_EXIST
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        # 获取用户当前policy中禁用列表
        policy = await EmbyClient.get_policy_dict(user.emby_id)
        if not policy:
            logger.error(f'用户policy获取失败(启用媒体库)，emby_id={user.emby_id}')
            return ServiceResultType.EMBY_SERVICE_ERROR
        user_blocked_list = policy.get('BlockedMediaFolders', [])  # type:list
        # 要开启的媒体库必须不是禁止的媒体库，或者用户被允许也可以
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')
        # 过滤不符合要求的库
        for item in enable_list:
            if item in blocked_libs:
                if item not in allowed_libs:
                    return ServiceResultType.LIBRARY_RESTRICTED
                elif item in user_blocked_list:
                    user_blocked_list.remove(item)
            elif item in user_blocked_list:
                user_blocked_list.remove(item)
        # 更新policy
        policy['BlockedMediaFolders'] = user_blocked_list
        edit_result = await EmbyClient.edit_policy(user.emby_id, json.dumps(policy))
        if not edit_result:
            logger.error(f'用户policy修改失败(启用媒体库)，emby_id={user.emby_id}')
            return ServiceResultType.EMBY_SERVICE_ERROR
    return ServiceResultType.SUCCESS


# 禁用媒体库
async def disable_libs(tgid, block_list):
    # 检查不存在的媒体库并清理
    await cleanup_invalid_lib_config(tgid)
    # 获取emby拥有的所有库名称
    libs_name = await get_emby_libs_name()
    # 判断输入列表的库是否存在
    for item in block_list:
        if item not in libs_name:
            return ServiceResultType.LIBRARY_NOT_EXIST
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        # 获取用户当前policy中禁用列表
        policy = await EmbyClient.get_policy_dict(user.emby_id)
        if not policy:
            logger.error(f'用户policy获取失败(禁用媒体库)，emby_id={user.emby_id}')
            return ServiceResultType.EMBY_SERVICE_ERROR
        user_blocked_list = policy.get('BlockedMediaFolders', [])  # type:list
        for item in block_list:
            if item not in user_blocked_list:
                user_blocked_list.append(item)
        # 更新policy
        policy['BlockedMediaFolders'] = user_blocked_list
        edit_result = await EmbyClient.edit_policy(user.emby_id, json.dumps(policy))
        if not edit_result:
            logger.error(f'用户policy修改失败(禁用媒体库)，emby_id={user.emby_id}')
            return ServiceResultType.EMBY_SERVICE_ERROR
    return ServiceResultType.SUCCESS


# 获取emby的媒体库名称列表
async def get_emby_libs_name():
    libs_name = []
    for item in await EmbyClient.get_virtual_libs():
        libs_name.append(item.get('Name'))
    return libs_name


# 媒体库禁用功能是否开启
async def is_block_enabled():
    blocked_lib_list = CommonUtils.get_from_conf('blocked_libs')
    if CommonUtils.is_not_empty(blocked_lib_list):
        return True
    return False


# 清理用户不存在的媒体库配置
async def cleanup_invalid_lib_config(tgid):
    # 对比配置文件中是否有不存在的媒体库名称，如果有则删除
    emby_libs = await get_emby_libs_name()  # type:list
    file_libs = CommonUtils.get_from_conf('blocked_libs')  # type:list
    if file_libs is None:
        file_libs = []
    for item in file_libs:
        if item not in emby_libs:
            logger.info(f'禁用媒体库配置中：媒体库 {item} 在emby中不存在，已删除')
            file_libs.remove(item)
    CommonUtils.save_to_conf('blocked_libs', file_libs)
    # 查看该用户的allowed_libs中是否有不存在的媒体库名称，如果有则删除
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')  # type:list
        for item in allowed_libs:
            if item not in emby_libs:
                logger.info(f'用户允许访问媒体库中：{item} 在emby中不存在，已删除')
                allowed_libs.remove(item)
        if CommonUtils.is_not_empty(allowed_libs):
            user.allowed_libs = ','.join(allowed_libs)
        else:
            user.allowed_libs = None
        await session.commit()
    return ServiceResultType.SUCCESS


# 清理emby用户policy禁止媒体库中不存在的项
async def cleanup_invalid_lib_emby_policy(emby_id):
    policy = await EmbyClient.get_policy_dict(emby_id)
    blocked_list = policy.get('BlockedMediaFolders', [])
    emby_libs = await get_emby_libs()
    for item in blocked_list:
        if item not in emby_libs:
            blocked_list.remove(item)
    if CommonUtils.is_not_empty(blocked_list):
        policy['BlockedMediaFolders'] = blocked_list
    else:
        policy['BlockedMediaFolders'] = None
    return await EmbyClient.edit_policy(emby_id, json.dumps(policy))


# 创建媒体库激活码
async def create_libs_codes(tgid, count, lib_list):
    if CommonUtils.is_empty(lib_list):
        return ServiceResultType.LIBRARY_NOT_EXIST
    # 获取emby拥有的所有库名称
    emby_libs = await get_emby_libs_name()
    # 检查输入列表中是否有不存在的媒体库
    for item in lib_list:
        if item not in emby_libs:
            return ServiceResultType.LIBRARY_NOT_EXIST
    library_code_list = []
    code_list = []
    for i in range(count):
        code_str = f'{lib_code_prefix}{str(uuid.uuid4())}'
        lib_code = LibraryCode(code=code_str, libs=','.join(lib_list), create_by=tgid,
                               create_time=datetime.datetime.now())
        library_code_list.append(lib_code)
        code_list.append(code_str)
    async with AsyncSession(engine) as session:
        session.add_all(library_code_list)
        await session.commit()
        return code_list


# 激活媒体库兑换码
async def redeem_libs_code(tgid, libs_code):
    async with AsyncSession(engine) as session:
        # 判断当前用户是否可以注册，或者当前用户是否已注册
        result = await session.execute(select(User).where(User.tgid == tgid).where(User.emby_id.is_not(None)))
        user = result.scalar_one_or_none()  # type:User
        if user is None:
            return ServiceResultType.ACCOUNT_NOT_EXIST
        allowed_libs = []
        if user.allowed_libs is not None:
            allowed_libs = user.allowed_libs.split(',')
        result = await session.execute(
            select(LibraryCode)
            .where(LibraryCode.code == libs_code)
        )
        library_code = result.scalar_one_or_none()  # type:LibraryCode
        if library_code is None:
            return ServiceResultType.LIBRARY_CODE_NOT_EXIST
        if library_code.is_used:
            return ServiceResultType.LIBRARY_CODE_ALREADY_USED
        libs = library_code.libs.split(',')
        for item in libs:
            if item not in allowed_libs:
                allowed_libs.append(item)
        user.allowed_libs = ','.join(allowed_libs)
        library_code.is_used = True
        library_code.update_time = datetime.datetime.now()
        library_code.used_by = tgid
        await session.commit()
        # tg_user = await app.get_users(tgid)
        # logger.info(
        #     f"成功：媒体库兑换码兑换成功 用户(tgid='{tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={user.emby_name},emby_id={user.emby_id})")
        return ServiceResultType.SUCCESS
