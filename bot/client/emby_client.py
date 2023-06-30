import asyncio
import json
from datetime import datetime

import aiohttp
import requests

from bot.client import aiohttp_session
from bot.decorator.aiohttp_retry import aiohttp_retry
from bot.log import logger
from config import *
from bot.user_policy_template import policy_template_json


class EmbyClient:

    # 获取emby榜单
    @staticmethod
    @aiohttp_retry(3)
    async def get_emby_rank(days, rank_type):
        today = datetime.today().date().strftime('%Y-%m-%d')
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        params = {
            "days": days,
            "end_date": today,
            'X-Emby-Token': embyapi
        }
        url = f'{embyurl}/emby/user_usage_stats/{rank_type.value}'
        async with aiohttp_session.get(url, headers=headers, params=params, timeout=10) as resp:
            if not resp.ok or resp.status >= 300 or resp.status < 200:
                return False
            return await resp.json()

    # 重置密码
    @staticmethod
    @aiohttp_retry(3)
    async def reset_password(emby_id):
        async with aiohttp_session.post(f'{embyurl}/Users/{emby_id}/Password',
                                        headers={"X-MediaBrowser-Token": embyapi},
                                        json={"resetPassword": True}) as resp:
            if resp.status == 204:
                return True
            else:
                return False

    @staticmethod
    @aiohttp_retry(3)
    # 查看库存数量
    async def items_count():
        async with aiohttp_session.get(f'{embyurl}/Items/Counts?api_key={embyapi}') as resp:
            text = await resp.text()
            r = json.loads(text)
            MovieCount = r['MovieCount']
            SeriesCount = r['SeriesCount']
            EpisodeCount = r['EpisodeCount']
            return MovieCount, SeriesCount, EpisodeCount

    @staticmethod
    @aiohttp_retry(3)
    # 获取用户信息
    async def get_user_info(emby_id):
        async with aiohttp_session.get(f"{embyurl}/emby/users/{emby_id}?api_key={embyapi}") as resp:
            text = await resp.text()
            return json.loads(text)

    @staticmethod
    @aiohttp_retry(3)
    # 新建用户
    async def create_user(username, is_copy_create=False):
        data = '{"Name":"' + username + '","HasPassword":true}'
        if is_copy_create:
            data = {
                "Name": username,
                "CopyFromUserId": prototype_account_id,
                "UserCopyOptions": ["UserPolicy", "UserConfiguration"],
            }
            data = json.dumps(data)
        params = (('api_key', embyapi),)
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        async with aiohttp_session.post(url=embyurl + '/emby/Users/New', headers=headers, params=params,
                                        data=data) as resp:
            text = await resp.text()
            return json.loads(text)

    @staticmethod
    @aiohttp_retry(3)
    # 修改policy
    async def edit_policy(emby_id, policy_json=None):
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        params = (('api_key', embyapi),)
        if policy_json is None:
            policy_json = policy_template_json
        async with aiohttp_session.post(embyurl + '/emby/Users/' + emby_id + '/Policy', headers=headers,
                                        params=params, data=policy_json) as resp:
            if resp.status == 204:
                return True
            return False

    @staticmethod
    @aiohttp_retry(3)
    # 修改密码
    async def change_password(emby_id, old_password, new_password):
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        data = '{"CurrentPw":"' + old_password + '" , "NewPw":"' + new_password + '","ResetPassword" : false}'
        async with aiohttp_session.post(f"{embyurl}/emby/users/{emby_id}/Password?api_key={embyapi}", headers=headers,
                                        data=data) as resp:
            if resp.status == 204:
                return True
            return False

    @staticmethod
    @aiohttp_retry(3)
    # 获取用户policy
    async def get_policy_dict(emby_id):
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        params = (('api_key', embyapi),)
        async with aiohttp_session.get(embyurl + '/emby/Users/' + emby_id, headers=headers, params=params) as resp:
            result = await resp.json()
            return result.get('Policy', None)

    @staticmethod
    @aiohttp_retry(3)
    # 删除用户
    async def delete_emby(user_id):
        headers = {
            "Content-Type": "application/json",
            "X-Emby-Token": embyapi,
        }
        # 发送 DELETE 请求
        async with aiohttp_session.delete(f"{embyurl}/Users/{user_id}", headers=headers) as resp:
            if resp.status == 204:
                return True
            return False

    @staticmethod
    @aiohttp_retry(3)
    # 获取媒体库信息
    async def get_virtual_libs():
        async with aiohttp_session.get(f"{embyurl}/emby/Library/VirtualFolders?api_key={embyapi}") as resp:
            libs = await resp.json()
            return libs
