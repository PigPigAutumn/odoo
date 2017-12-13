# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import _
import werkzeug
from odoo.exceptions import AccessError
import logging
import odoo.addons.web.controllers.main as main
import odoo
import pprint

class LoginController(main.Home):

    @http.route('/web/login/', auth='none', type='http', sitemap=False)
    def login(self, redirect=None, *args, **kwargs):
        """继承登录模块,修改登录界面,添加密码加密比对等的功能"""
        main.ensure_db()
        # 重新登录
        request.params['login_success'] = False

        # ???这一段代码不知道拿来干嘛的
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)
        # 如果没有uid,则设uid为admin
        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        vals = request.params.copy()
        try:
            vals['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            vals['databases'] = None
        # 如果不是请求登录的话,request.httprequest.method为GET,请求登录才会为POST
        if request.httprequest.method == 'POST':
            # 请求登录
            # todo 以后登录模块需要做BCrypt密码加密的工作,前端js与后台逻辑都要改
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                # 登录成功,置登录状态为true
                request.params['login_success'] = True
                # 跳转到刚刚请求的页面
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            request.uid = old_uid
            vals['error'] = _("Wrong login/password")
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                vals['error'] = _('Only employee can access this database. Please contact the administrator.')

        if 'login' not in vals and request.session.get('auth_login'):
            vals['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            vals['disable_database_manager'] = True

        response = request.render('pig-builder.login_page', vals)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/web/', auth='user', type='http')
    def homepage(self, **kwargs):
        main.ensure_db()
        if not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)
        if kwargs.get('redirect'):
            return werkzeug.utils.redirect(kwargs.get('redirect'), 303)

        request.uid = request.session.uid
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            dashboard = request.env['ir.model.data'].xmlid_to_object('web_settings_dashboard.web_dashboard_menu')
            context['dashboard_menu_id'] = dashboard.id
            context['dashboard_action_id'] = dashboard.action.id
            response = request.render('pig-builder.homepage', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')

    @http.route('/web/registry', auth='none', type='http')
    def registry(self, **kwargs):
        main.ensure_db()
        if not request.session.uid:
            request.uid = odoo.SUPERUSER_ID

        # if request.httprequest.method == 'GET':
        #     # 只是请求注册页
        #     return request.render('pig-builder.registry_page', {})
        #
        # if request.httprequest.method == 'POST':
        #     # 提交数据,请求注册
        #     vals = request.params.copy()
        #     if vals['user_type'] == 'teacher':
        #         # 教师注册
        #         # todo 应该与其他模型关联的
        #         teacher = request.env['res.teacher'].create({
        #             'name': vals['name'],
        #             'country': vals['country'],
        #             'province': vals['province'],
        #             'city': vals['city'],
        #             'school': vals['school'],
        #             'academy': vals['academy'],
        #             'password': vals['password'],
        #         })
        #         if teacher:
        #             request.session.authenticate(request.session.db, teacher.login,
        #                                          teacher.password)
        #             return request.render('pig-builder.homepage', {})
        #     else:
        #         student = request.env['res.student'].create({
        #             'name': vals['name'],
        #             'number': vals['number'],
        #             'country': vals['country'],
        #             'province': vals['province'],
        #             'city': vals['city'],
        #             'school': vals['school'],
        #             'academy': vals['academy'],
        #             'password': vals['password'],
        #         })
        #         if student:
        #             request.session.authenticate(request.session.db, student.login,
        #                                          student.password)

        return request.render('pig-builder.registry_page', {})