# -*- coding: utf-8 -*-
{
    'name': "大学课程题库建设系统-redis_session共享模块",

    'summary': """
        大学课程题库建设系统所使用的,将session都存于redis中,以达到共享session的目的
    """,
    'description': """
        大学课程题库建设系统所使用的,将session都存于redis中,以达到共享session的目的
    """,

    'author': "猪屎秋(pigpigAutumn)",
    'website': "https://github.com/PigPigAutumn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': 'beta',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web'],

    # always loaded
    'data': [],
    # only loaded in demonstration mode
    'demo': [],
    'application': False,
}
