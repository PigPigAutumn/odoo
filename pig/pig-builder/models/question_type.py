# -*- coding: utf-8 -*-
from odoo import fields,models

class QuestionType(models.Model):
    _name = 'question.type'

    name = fields.Char(string=u'题型', required=True)
    value = fields.Integer(string=u'题型编号', required=True)
