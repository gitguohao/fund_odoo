# coding: utf-8
from odoo import models, fields
from extra_addons.tools import regular


class IndicatorsConfig(models.Model):
    _name = 'indicators.config'
    _description = u'指标管理'
    code = fields.Char(string='编码', regular=regular, tips='编码只能输入字母或汉字!')
    name = fields.Char(string='名称')
    english = fields.Char(string='英文')
    formula = fields.Char(string='公式')
    remark = fields.Char(string='说明')

    _sql_constraints = [
        ('unique_code', 'unique (code)', '编码必须唯一!')
    ]
