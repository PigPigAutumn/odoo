# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import _
import werkzeug
from odoo.exceptions import AccessError
import logging


class Setting(http.Controller):
    @http.route('/web/setting', type='http', auth='user')
    def setting(self):
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            return request.render('web.webclient_bootstrap', qcontext=context)
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')