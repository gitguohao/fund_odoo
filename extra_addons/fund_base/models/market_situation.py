# coding: utf-8
from odoo import models, fields


class MarketSituation(models.Model):
    _name = 'market.situation'
    _description = u'大盘行情数据'
    code = fields.Char(string='指数代码')
    name = fields.Char(string='指数名称')
    opening_quotation = fields.Float(string='最新开盘点位')
    close_quoation = fields.Float(string='最新收盘点位')
    last_transaction_date = fields.Date(string='最新交易日')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='所属交易日')
    remark = fields.Char(string='备注')
    market_day_situation_ids = fields.One2many('market.day.situation', 'market_situation_id', string='日行情')

    def get_market_situation(self, b_date, e_date, **kwargs):
        transaction_dates = self.transaction_date_config_id.get_transaction_dates(b_date, e_date)
        datas = self.env['market.day.situation'].search_read([
            ('dates', 'in', transaction_dates),
        ], ['dates', 'close_quoation'])
        return datas


class MarketDaySituation(models.Model):
    _name = 'market.day.situation'
    _description = u'日行情'
    dates = fields.Date('交易日')
    opening_quotation = fields.Float('开盘点位', digits=(16, 4))
    close_quoation = fields.Float('收盘点位', digits=(16, 4))
    interest_rate = fields.Float(string='日收益率', digits=(16, 4))
    market_situation_id = fields.Many2one('market.situation', string='大盘行情数据')


