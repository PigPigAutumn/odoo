# -*- coding: utf-8 -*-
import pickle
from odoo import http, tools
import werkzeug.contrib.sessions
from odoo.tools.func import lazy_property

SESSION_TIME = 60 * 60 * 24 * 7 # session过期时间默认为一周


def is_redis_session_store_actived():
    """从配置文件中读取配置,判断是否启用redis存储session"""
    return tools.config.get('enable_redis')

# 导入redis,如果没有安装redis的话则抛出异常
try:
    import redis
except ImportError:
    if is_redis_session_store_actived():
        raise ImportError(u'python库:redis 还没有安装哦')


class PigRedisSessionStore(werkzeug.contrib.sessions.SessionStore):
    """替换odoo原本的session_store,使session存储在redis中"""

    def __init__(self, *args, **kwargs):
        super(PigRedisSessionStore, self).__init__(*args, **kwargs)
        self.expire = kwargs.get('expire', SESSION_TIME)
        self.key_prefix = kwargs.get('key_prefix', '')
        # 初始化redis,从odoo的配置文件里读取相关的redis配置
        self.redis = redis.Redis(host=tools.config.get('redis_host', 'localhost'),
                                 port=int(tools.config.get('redis_port', 6379)),
                                 db=int(tools.config.get('redis_session_db', 0)),
                                 password=tools.config.get('redis_password', None))
        # 判断服务器上redis服务是否正在运行
        self._is_redis_server_running()

    def save(self, session):
        """存session到redis中,并设置过期时间"""
        key = self._get_session_key(session.sid)
        data = pickle.dumps(dict(session))
        self.redis.setex(key, data, self.expire)

    def _get_session_key(self, sid):
        key = self.key_prefix + sid
        if isinstance(key, str):
            key = key.encode('utf-8')
        return key

    def delete(self, session):
        """删除session"""
        key = self._get_session_key(session.sid)
        self.redis.delete(key)

    def get(self, sid):
        key = self._get_session_key(sid)
        data = self.redis.get(key)
        if data:
            self.redis.setex(key, data, self.expire)
            data = pickle.loads(data)
        else:
            data = {}
        return self.session_class(data, sid, False)

    def _is_redis_server_running(self):
        try:
            self.redis.ping()
        except redis.ConnectionError:
            raise redis.ConnectionError(u'redis服务器没有开启')

if is_redis_session_store_actived():
    # 如果开启了redis存储session,则覆盖替换odoo原本存储session的逻辑

    def session_gc(session_store):
        # 覆盖odoo原本的session_gc方法,该方法原本为将过期的session file删除,但是存储在redis里面的话就不会有本地文件
        pass

    @lazy_property
    def session_store(self):
        # 原本的session_store是用fileSystem存储在本地的,现在改为存储在redis
        return PigRedisSessionStore(session_class=http.OpenERPSession)

    http.session_gc = session_gc
    http.Root.session_store = session_store
