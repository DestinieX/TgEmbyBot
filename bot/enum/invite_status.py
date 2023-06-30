# 邀请码使用状态枚举类

from bot.enum import *


class InviteStatus(enum.Enum):
    NOT_FOUND = '没有找到这个邀请码'
    ALREADY_USED = '邀请码已被使用'
    REGISTRATION_GRANTED = '已获得注册资格，邀请码已失效'
    ALREADY_REGISTERED = '您已有账号或已经获得注册资格，请不要重复使用邀请码'
    CODE_EXPIRED = '邀请码已过期'
