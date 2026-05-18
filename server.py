import dash
import re
from flask import request
from user_agents import parse
from flask_principal import Principal, Permission, RoleNeed, identity_loaded
from flask_login import LoginManager, UserMixin, current_user, AnonymousUserMixin

# 应用基础参数
from models.users import Users
from configs import BaseConfig, AuthConfig

from datetime import datetime, timedelta
# from apscheduler.schedulers.background import BackgroundScheduler
# from utils.market_data_sync import run_daily_sync_task


external_js = [
    'https://registry.npmmirror.com/klinecharts/9.8.10/files/dist/umd/klinecharts.min.js'
]

class CustomDash(dash.Dash):
    def interpolate_index(self, **kwargs):
        scripts = kwargs.pop("scripts")

        # 1. 提取所有 http 开头的 script 标签
        external_scripts = re.findall('(<script src="http.*?"></script>)', scripts)

        for external_script in external_scripts:
            # 2. 提取 src 内部的 URL
            src_match = re.findall('"(.*?)"', external_script)
            if not src_match:
                continue
            
            origin_library_src = src_match[0]

            # 3. 提取关键信息 (增加对末尾可能存在的查询参数的兼容)
            # 修改正则：不强制 $ 结尾，防止有 ?v=xxx 等干扰
            match_res = re.findall("com/(.+)@(.+?)/([^?#]+)", origin_library_src)
            
            if match_res:
                # 只有匹配成功才进行解包
                result = match_res[0]
                library_name, library_version, library_file = result
                
                # 4. 基于 npmmirror 构建新的资源地址
                new_library_src = f"https://registry.npmmirror.com/{library_name}/{library_version}/files/{library_file}"
                scripts = scripts.replace(origin_library_src, new_library_src)
            else:
                # 如果匹配失败，打印一下看看是哪个 URL 没匹配上，方便调试
                # print(f"Skipping URL: {origin_library_src}")
                pass

        return super(CustomDash, self).interpolate_index(scripts=scripts, **kwargs)


app = CustomDash(
    __name__,
    title=BaseConfig.app_title,
    suppress_callback_exceptions=True,
    compress=True,  # 隐式依赖flask-compress
    serve_locally=False,
    update_title=None,
    external_scripts=external_js
)
server = app.server

# 设置应用密钥
app.server.config["SECRET_KEY"] = BaseConfig.app_secret_key
app.server.config["SESSION_COOKIE_NAME"] = BaseConfig.app_session_cookie_name

# 为当前应用添加flask-login用户登录管理
login_manager = LoginManager()
login_manager.init_app(app.server)

# 为当前应用添加flask-principal权限管理
principals = Principal(app.server)

# ===========================
# 新增：配置定时任务调度器
# ===========================
# scheduler = BackgroundScheduler()

# 添加定时任务：每天下午 17:00 执行数据同步
# 考虑到收盘后数据整理，建议设置在 16:00 或 17:00 以后
# scheduler.add_job(
#     func=run_daily_sync_task, 
#     trigger='cron', 
#     hour=17, 
#     minute=0, 
#     id='daily_market_sync',
#     replace_existing=True
# )

# 可选：在启动时立即执行一次（用于测试，生产环境可注释掉）
# scheduler.add_job(func=run_daily_sync_task, trigger='date', run_date=datetime.now() + timedelta(seconds=10))

# 启动调度器
# 注意：在 Debug 模式下 Flask reloader 会导致 scheduler 运行两次，可以使用 use_reloader=False 解决
# 或者简单判断一下是否为主进程
# if not scheduler.running:
#     scheduler.start()


class User(UserMixin):
    """flask-login专用用户类"""

    def __init__(
        self, id: str, user_name: str, user_role: str, session_token: str = None
    ) -> None:
        """初始化用户信息"""

        self.id = id
        self.user_name = user_name
        self.user_role = user_role
        self.session_token = session_token


@login_manager.user_loader
def user_loader(user_id):
    """flask-login内部专用用户加载函数"""

    # 避免非关键请求触发常规用户加载逻辑
    if any(
        [
            request.path in ["/_reload-hash", "/_dash-layout", "/_dash-dependencies"],
            request.path.startswith("/assets/"),
            request.path.startswith("/_dash-component-suites/"),
        ]
    ):
        return AnonymousUserMixin()

    # 根据当前要加载的用户id，从数据库中获取匹配用户信息
    match_user = Users.get_user(user_id)

    # 处理未匹配到有效用户的情况
    if not match_user:
        return AnonymousUserMixin()

    # 当前用户实例化
    user = User(
        id=match_user.user_id,
        user_name=match_user.user_name,
        user_role=match_user.user_role,
        session_token=match_user.session_token,
    )

    return user


# 定义不同用户角色
user_permissions = {role: Permission(RoleNeed(role)) for role in AuthConfig.roles}


@identity_loaded.connect_via(app.server)
def on_identity_loaded(sender, identity):
    """flask-principal身份加载回调函数"""

    identity.user = current_user

    if hasattr(current_user, "user_role"):
        identity.provides.add(RoleNeed(current_user.user_role))


@app.server.before_request
def check_browser():
    """检查浏览器版本是否符合最低要求"""

    # 提取当前请求对应的浏览器信息
    user_agent = parse(str(request.user_agent))

    # 若浏览器版本信息有效
    if user_agent.browser.version != ():
        # IE相关浏览器直接拦截
        if user_agent.browser.family == "IE":
            return (
                "<div style='font-size: 16px; color: red; position: fixed; top: 40%; left: 50%; transform: translateX(-50%);'>"
                "请不要使用IE浏览器，或开启了IE内核兼容模式的其他浏览器访问本应用</div>"
            )
        # 基于BaseConfig.min_browser_versions配置，对相关浏览器最低版本进行检查
        for rule in BaseConfig.min_browser_versions:
            # 若当前请求对应的浏览器版本，低于声明的最低支持版本
            if (
                user_agent.browser.family == rule["browser"]
                and user_agent.browser.version[0] < rule["version"]
            ):
                return (
                    "<div style='font-size: 16px; color: red; position: fixed; top: 40%; left: 50%; transform: translateX(-50%);'>"
                    "您的{}浏览器版本低于本应用最低支持版本（{}），请升级浏览器后再访问</div>"
                ).format(rule["browser"], rule["version"])

        # 若开启了严格的浏览器类型限制
        if BaseConfig.strict_browser_type_check:
            # 若当前浏览器不在声明的浏览器范围内
            if user_agent.browser.family not in [
                rule["browser"] for rule in BaseConfig.min_browser_versions
            ]:
                return (
                    "<div style='font-size: 16px; color: red; position: fixed; top: 40%; left: 50%; transform: translateX(-50%);'>"
                    "当前浏览器类型不在支持的范围内，支持的浏览器类型有：{}</div>"
                ).format(
                    "、".join(
                        [rule["browser"] for rule in BaseConfig.min_browser_versions]
                    )
                )
