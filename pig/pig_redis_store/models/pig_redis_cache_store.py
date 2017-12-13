from decorator import decorator
from inspect import formatargspec, getargspec
from pickle import dumps, loads, HIGHEST_PROTOCOL
from inspect import isfunction
from collections import defaultdict
from hashlib import md5
import threading
from odoo.tools import assertion_report
from odoo import tools
import cloudpickle
import odoo
from odoo.modules.registry import Registry

unsafe_eval = eval
LOCAL_CACHE = {}

import logging
_logger = logging.getLogger(__name__)


def is_redis_cache_store_actived():
    """从配置文件中读取配置,判断是否启用redis存储session"""
    return tools.config.get('enable_redis')

# 导入redis,如果没有安装redis的话则抛出异常
try:
    import redis
except ImportError:
    if is_redis_cache_store_actived():
        raise ImportError(u'python库:redis 还没有安装哦')


class ormcache_counter(object):
    """ Statistic counters for cache entries. """
    __slots__ = ['hit', 'miss', 'err']

    def __init__(self):
        self.hit = 0
        self.miss = 0
        self.err = 0

    @property
    def ratio(self):
        return 100.0 * self.hit / (self.hit + self.miss or 1)

# statistic counters dictionary, maps (dbname, modelname, method) to counter
STAT = defaultdict(ormcache_counter)


class ormcache(object):
    """ LRU cache decorator for model methods.
    The parameters are strings that represent expressions referring to the
    signature of the decorated method, and are used to compute a cache key::

        @ormcache('model_name', 'mode')
        def _compute_domain(self, model_name, mode="read"):
            ...

    For the sake of backward compatibility, the decorator supports the named
    parameter `skiparg`::

        @ormcache(skiparg=1)
        def _compute_domain(self, model_name, mode="read"):
            ...
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.skiparg = kwargs.get('skiparg')
        self.stat_miss = 0
        self.stat_hit = 0
        self.stat_err = 0
        self.redis = redis.Redis(host=tools.config.get('redis_host', 'localhost'),
                                 port=int(tools.config.get('redis_port', 6379)),
                                 db=int(tools.config.get('redis_cache_db', 1)),
                                 password=tools.config.get('redis_password', None))
        self.timeout = 60 * 60 * 24 # 缓存过期时间为1天

    def __call__(self, method):
        self.method = method
        self.determine_key()
        lookup = decorator(self.lookup, method)
        lookup.clear_cache = self.clear
        return lookup

    def determine_key(self):
        """ Determine the function that computes a cache key from arguments. """
        if self.skiparg is None:
            # build a string that represents function code and evaluate it
            args = formatargspec(*getargspec(self.method))[1:-1]
            if self.args:
                code = "lambda %s: (%s,)" % (args, ", ".join(self.args))
            else:
                code = "lambda %s: ()" % (args,)
            self.key = unsafe_eval(code)
        else:
            # backward-compatible function that uses self.skiparg
            self.key = lambda *args, **kwargs: args[self.skiparg:]

    def lru(self, model):
        counter = STAT[(model.pool.db_name, model._name, self.method)]
        return model.pool.cache, (model._name, self.method), counter

    def lookup(self, method, *args, **kwargs):
        # if getattr(args[0], '_name', False) == 'ir.qweb':
            # return self.method(*args, **kwargs)
        # key = md5(str(self.key(*args, **kwargs))).hexdigest()

        if getattr(args[0], '_name', False) == 'ir.qweb':
            key = md5(str(str(id(args[0])) + str(self.key(*args, **kwargs))).encode('utf-8')).hexdigest()
        else:
            key = md5(str(self.key(*args, **kwargs)).encode('utf-8')).hexdigest()

        db_name = args[0].pool.db_name
        model_name = args[0]._name
        htable = 'oe-cache:%s %s %s' % (db_name, model_name, method.__name__)

        value = self.redis.hget(htable, key)
        UUID = '3902f8a3-cabe-11e7-84f8-6c40088e0e3c|' # 特征码
        if value:
            self.stat_hit += 1
            if isinstance(value, str) and value.startswith(UUID):
                fn_code = value.split(UUID)[1]
                return cloudpickle.loads(fn_code)
            return loads(value)
        else:
            self.stat_miss += 1
            value = self.method(*args, **kwargs)
            if isfunction(value):
                fn_code = '%s%s' %  (UUID, cloudpickle.dumps(value))
                self.redis.hset(htable, key, fn_code)
            else:
                self.redis.hset(htable, key, dumps(value, HIGHEST_PROTOCOL))
            self.redis.expire(htable, self.timeout)
            return value
        # d, key0, counter = self.lru(args[0])
        # key = key0 + self.key(*args, **kwargs)
        # try:
        #     r = d[key]
        #     counter.hit += 1
        #     return r
        # except KeyError:
        #     counter.miss += 1
        #     value = d[key] = self.method(*args, **kwargs)
        #     return value
        # except TypeError:
        #     counter.err += 1
        #     return self.method(*args, **kwargs)

    def clear(self, model, *args):
        """ Remove *args entry from the cache or all keys if *args is undefined """
        db_name = model.pool.db_name
        model_name = model._name
        htable = 'oe-cache:%s %s %s' % (db_name, model_name, self.method.__name__)
        ret = self.redis.delete(htable)
        model.pool._any_cache_cleared = True
        # """ Clear the registry cache """
        # d, key0, _ = self.lru(model)
        # d.clear()
        # model.pool.cache_cleared = True


class ormcache_context(ormcache):
    """ This LRU cache decorator is a variant of :class:`ormcache`, with an
    extra parameter ``keys`` that defines a sequence of dictionary keys. Those
    keys are looked up in the ``context`` parameter and combined to the cache
    key made by :class:`ormcache`.
    """
    def __init__(self, *args, **kwargs):
        super(ormcache_context, self).__init__(*args, **kwargs)
        self.keys = kwargs['keys']

    def determine_key(self):
        """ Determine the function that computes a cache key from arguments. """
        assert self.skiparg is None, "ormcache_context() no longer supports skiparg"
        # build a string that represents function code and evaluate it
        spec = getargspec(self.method)
        args = formatargspec(*spec)[1:-1]
        cont_expr = "(context or {})" if 'context' in spec.args else "self._context"
        keys_expr = "tuple(map(%s.get, %r))" % (cont_expr, self.keys)
        if self.args:
            code = "lambda %s: (%s, %s)" % (args, ", ".join(self.args), keys_expr)
        else:
            code = "lambda %s: (%s,)" % (args, keys_expr)
        self.key = unsafe_eval(code)


class ormcache_multi(ormcache):
    """ This LRU cache decorator is a variant of :class:`ormcache`, with an
    extra parameter ``multi`` that gives the name of a parameter. Upon call, the
    corresponding argument is iterated on, and every value leads to a cache
    entry under its own key.
    """
    def __init__(self, *args, **kwargs):
        super(ormcache_multi, self).__init__(*args, **kwargs)
        self.multi = kwargs['multi']

    def determine_key(self):
        """ Determine the function that computes a cache key from arguments. """
        assert self.skiparg is None, "ormcache_multi() no longer supports skiparg"
        assert isinstance(self.multi, str), "ormcache_multi() parameter multi must be an argument name"

        super(ormcache_multi, self).determine_key()

        # key_multi computes the extra element added to the key
        spec = getargspec(self.method)
        args = formatargspec(*spec)[1:-1]
        code_multi = "lambda %s: %s" % (args, self.multi)
        self.key_multi = unsafe_eval(code_multi)

        # self.multi_pos is the position of self.multi in args
        self.multi_pos = spec.args.index(self.multi)

    def lookup(self, method, *args, **kwargs):
        db_name = args[0].pool.db_name
        model_name = args[0]._name
        htable = 'oe-cache:%s %s %s' % (db_name, model_name, method.__name__)

        base_key = self.key(*args, **kwargs)
        ids = self.key_multi(*args, **kwargs)
        result = {}
        missed = []

        # first take what is available in the cache
        for i in ids:
            key = base_key + (i,)
            key = md5(str(key).encode('utf-8')).hexdigest()
            value = self.redis.hget(htable, key)
            if value:
                result[i] = loads(value)
                self.stat_hit += 1
            else:
                self.stat_miss += 1
                missed.append(i)

        if missed:
            # call the method for the ids that were not in the cache
            args = list(args)
            args[self.multi_pos] = missed
            result.update(method(*args, **kwargs))

            # store those new results back in the cache
            for i in missed:
                key = base_key + (i,)
                key = md5(str(key).encode('utf-8')).hexdigest()
                self.redis.hset(htable, key, dumps(result[i], HIGHEST_PROTOCOL))
                self.redis.expire(htable, self.timeout)

        return result
        # d, key0, counter = self.lru(args[0])
        # base_key = key0 + self.key(*args, **kwargs)
        # ids = self.key_multi(*args, **kwargs)
        # result = {}
        # missed = []
        #
        # # first take what is available in the cache
        # for i in ids:
        #     key = base_key + (i,)
        #     try:
        #         result[i] = d[key]
        #         counter.hit += 1
        #     except Exception:
        #         counter.miss += 1
        #         missed.append(i)
        #
        # if missed:
        #     # call the method for the ids that were not in the cache; note that
        #     # thanks to decorator(), the multi argument will be bound and passed
        #     # positionally in args.
        #     args = list(args)
        #     args[self.multi_pos] = missed
        #     result.update(method(*args, **kwargs))
        #
        #     # store those new results back in the cache
        #     for i in missed:
        #         key = base_key + (i,)
        #         d[key] = result[i]
        #
        # return result


def log_ormcache_stats(sig=None, frame=None):
    """ Log statistics of ormcache usage by database, model, and method. """
    pass


def clear(self):
    self.d = {}
    self.first = None
    self.last = None

    self.redis = redis.Redis(host=tools.config.get('redis_host', 'localhost'),
                                 port=int(tools.config.get('redis_port', 6379)),
                                 db=int(tools.config.get('redis_cache_db', 1)),
                                 password=tools.config.get('redis_password', None))
    if self.db_name:
        cache_htables = self.redis.keys('oe-cache:%s *' % self.db_name)
        for htable in cache_htables:
            self.redis.delete(htable)


def LRU_init(self, count, pairs=[], db_name=''):
    self._lock = threading.RLock()
    self.count = max(count, 1)
    self.d = {}
    self.first = None
    self.last = None
    for key, value in pairs:
        self[key] = value
    # patch
    self.db_name = db_name


def Registry_init(self, db_name):
    super(Registry, self).__init__()
    self.models = {}  # model name/model instance mapping
    self._sql_error = {}
    self._store_function = {}
    self._pure_function_fields = {}  # {model: [field, ...], ...}
    self._init = True
    self._init_parent = {}
    self._assertion_report = assertion_report.assertion_report()
    self._fields_by_model = None

    # modules fully loaded (maintained during init phase by `loading` module)
    self._init_modules = set()

    self.db_name = db_name
    self._db = odoo.sql_db.db_connect(db_name)

    # special cursor for test mode; None means "normal" mode
    self.test_cr = None

    # Indicates that the registry is
    self.ready = False

    # Inter-process signaling (used only when openerp.multi_process is True):
    # The `base_registry_signaling` sequence indicates the whole registry
    # must be reloaded.
    # The `base_cache_signaling sequence` indicates all caches must be
    # invalidated (i.e. cleared).
    self.base_registry_signaling_sequence = None
    self.base_cache_signaling_sequence = None

    self.cache = odoo.tools.lru.LRU(8192, db_name=db_name)
    # Flag indicating if at least one model cache has been cleared.
    # Useful only in a multi-process context.
    self._any_cache_cleared = False

    cr = self.cursor()
    has_unaccent = odoo.modules.db.has_unaccent(cr)
    if odoo.tools.config['unaccent'] and not has_unaccent:
        _logger.warning("The option --unaccent was given but no unaccent() function was found in database.")
    self.has_unaccent = odoo.tools.config['unaccent'] and has_unaccent
    cr.close()


if is_redis_cache_store_actived():
    # 替换odoo的缓存方法
    odoo.tools.cache = ormcache
    odoo.tools.ormcache = ormcache
    odoo.tools.ormcache_context = ormcache_context
    odoo.tools.ormcache_multi = ormcache_multi
    odoo.tools.log_ormcache_stats = log_ormcache_stats
    odoo.service.server.log_ormcache_stats = log_ormcache_stats
    odoo.tools.lru.LRU.clear = clear
    odoo.modules.registry.LRU.clear = clear
    odoo.tools.lru.LRU.__init__ = LRU_init
    odoo.modules.registry.LRU.__init__ = LRU_init
    # odoo.modules.registry.Registry.__init__ = Registry_init

    from odoo.addons.base.ir.ir_qweb.qweb import frozendict

    def __setitem__(self, key, val):
        return super(frozendict, self).__setitem__(key, val)
    frozendict.__setitem__  = __setitem__
