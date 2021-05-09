# coding: utf-8
from odoo import models, fields


class FundBaseData(models.Model):
    _name = 'fund.base.data'
    _description = u'基金基础数据'
    code = fields.Char(string='编码')
    name = fields.Char(string='名称')
    last_price = fields.Float(string='最新现价', digits=(16, 4))
    last_price_date = fields.Datetime(string='最新现价时间')
    unit_net = fields.Float(string='单位净值', digits=(16, 4))
    total_net = fields.Float(string='累计净值', digits=(16, 4))
    types = fields.Char(string='类型')
    establish_date = fields.Date(string='成立日')
    fund_manager = fields.Char(string='基金经理人')
    manager = fields.Char(string='管理人')
    fund_base_day_net_ids = fields.One2many('fund.base.day.net', 'fund_base_data_id', string='日净值')


class FundBaseDayNet(models.Model):
    _name = 'fund.base.day.net'
    _description = u'日净值'
    dates = fields.Date('时间')
    beg_price = fields.Float('开盘价', digits=(16, 4))
    end_price = fields.Float('收盘价', digits=(16, 4))
    unit_net = fields.Float(string='单位净值', digits=(16, 4))
    total_net = fields.Float(string='累计净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('fund.base.data', string='基金基础数据')





