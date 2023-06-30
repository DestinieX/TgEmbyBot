import enum


class ServiceResultType(enum.Enum):
    SUCCESS = '成功'
    NOT_IN_DATABASE = '用户未入库，无信息'
    ACCOUNT_EXIST = '账号已存在'
    ACCOUNT_NOT_EXIST = '账号不存在'
    EMBY_NOT_EXIST = 'EMBY账号不存在'  # 仅表示根据emby_id无法获取到emby账号
    EMBY_BAN = 'EMBY账号已被封禁'
    EMBY_UNBAN = 'EMBY账号已解封'
    REGISTRATION_RESTRICTED = '注册受限，无注册资格'
    DO_NOTHING = '不进行任何处理'
    NOT_ELIGIBLE_FOR_REGISTRATION = '无注册资格'
    EMBY_USERNAME_EXIST = 'EMBY用户名已存在'
    TGID_NOT_EXIST = 'TGID错误/不存在'
    ADD_WHITELIST = '添加白名单'
    CANCEL_WHITELIST = '移除白名单'
    LIBRARY_NOT_EXIST = '媒体库不存在'
    LIBRARY_RESTRICTED = '无媒体库访问权限'
    EMBY_SERVICE_ERROR = 'EMBY业务执行异常'
    LIBRARY_CODE_NOT_EXIST = '媒体库激活码不存在'
    LIBRARY_CODE_ALREADY_USED = '媒体库激活码已使用'
    LIBRARY_GRANTED = '激活码已失效，媒体库权限已添加'

