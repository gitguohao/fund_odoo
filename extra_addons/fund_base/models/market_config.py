# coding: utf-8
from odoo import models, fields


class MarketConfig(models.Model):
    _name = 'market.config'
    _description = u'市场管理-时间区间设置'
    code = fields.Char(string='编码')
    name = fields.Char(string='名称')
    beg_date = fields.Date(string='开始时间')
    end_date = fields.Date(string='结束时间')
    remark = fields.Char('备注')
    _sql_constraints = [
        ('unique_code', 'unique (code)', '编码必须唯一!')
    ]