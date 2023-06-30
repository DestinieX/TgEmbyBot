from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message


class AppUtils:
    # 获取回复id

    @staticmethod
    def get_reply_id(message=''):
        try:
            tgid = message.reply_to_message.from_user.id
        except AttributeError:
            return None
        return tgid

    @staticmethod
    def is_private_chat(message=''):
        if str(message.chat.type) == 'ChatType.PRIVATE':
            return True
        else:
            return False

    @staticmethod
    # 判断用户是否在群组内
    async def is_user_in_group(app, chat_id, user_id):
        try:
            await app.get_chat_member(chat_id, user_id)
            return True
        except Exception as e:
            return False

    @staticmethod
    # 检测是否为成员退群事件
    def is_user_left_event(old_chat_member, new_chat_member):
        if new_chat_member is None and old_chat_member is not None:
            return True
        if old_chat_member is not None and new_chat_member is not None:
            # 判断被ban解除，不删除账号
            if old_chat_member.status == ChatMemberStatus.RESTRICTED and new_chat_member.status == ChatMemberStatus.MEMBER:
                return False
            # 被T+ban，删除账号
            if old_chat_member.status == ChatMemberStatus.MEMBER and new_chat_member.status == ChatMemberStatus.BANNED:
                return True
            # 禁止状态下退群，删除账号
            if old_chat_member.is_member and not new_chat_member.is_member:
                return True
        return False

    @staticmethod
    # 获取匿名管理员tgid
    async def get_anonymous_admin_tgid(client: Client, message: Message):
        author_signature = message.author_signature
        chat_id = message.chat.id
        chat_members = client.get_chat_members(chat_id=chat_id)
        async for chat_member in chat_members:
            if chat_member.custom_title == author_signature:
                return chat_member.user.id
        return None

    @staticmethod
    # 当前消息是否来源于匿名管理员
    async def is_anonymous_admin(message: Message):
        if message.from_user is None and message.sender_chat is not None:
            return True
        return False

    @staticmethod
    # 匿名管理员是否含有头衔
    async def has_author_signature(message: Message):
        if message.author_signature is not None:
            return True
        return False

