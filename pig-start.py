#!/usr/bin/env python3

import redis
import odoo

# 每次启动odoo时都清空以下缓存
print(u'########清空redis的缓存########')
r = redis.Redis(host=odoo.tools.config.get('redis_host', 'localhost'),
                port=int(odoo.tools.config.get('redis_port', 6379)),
                db=int(odoo.tools.config.get('redis_cache_db', 1)),
                password=odoo.tools.config.get('redis_password', None))
for key in r.keys():
    print(u'# key:' + str(key))
    r.delete(key)

print(u'##############################')

if __name__ == "__main__":
    odoo.cli.main()
