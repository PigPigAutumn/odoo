# -*- coding: utf-8 -*-
{
    'name': "大学课程题库建设系统",

    'summary': """
        这是一个大学课程题库建设系统
    """,
    'description': """
        与牛客网类似,该课程题库建设系统提供了试题创建,录入,试卷创建,导入,导出等功能
    """,

    'author': "猪屎秋(pigpigAutumn)",
    'website': "https://github.com/PigPigAutumn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': 'beta',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'pig_redis_store'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        'data/question_type.xml',
        'template/login_page.xml',
        'template/homepage.xml',
        'template/registry_page.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'application': True,
}