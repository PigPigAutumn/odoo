# -*- coding: utf-8 -*-
from odoo import http

# class Pig-builder(http.Controller):
#     @http.route('/pig-builder/pig-builder/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pig-builder/pig-builder/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pig-builder.listing', {
#             'root': '/pig-builder/pig-builder',
#             'objects': http.request.env['pig-builder.pig-builder'].search([]),
#         })

#     @http.route('/pig-builder/pig-builder/objects/<model("pig-builder.pig-builder"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pig-builder.object', {
#             'object': obj
#         })