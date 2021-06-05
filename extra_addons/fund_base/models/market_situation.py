# coding: utf-8
import xlrd
import base64
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

    _sql_constraints = [
        ('unique_code', 'unique (code)', '编码必须唯一!')
    ]

    def import_data(self, data):
        excel = xlrd.open_workbook(file_contents=base64.decodestring(data))
        sh = excel.sheet_by_index(0)
        cell_values = sh._cell_values
        for rx in range(sh.nrows):
            if rx == 0: continue
            code = cell_values[rx][0]
            name = cell_values[rx][1]
            dates = cell_values[rx][2]
            opening_quotation = cell_values[rx][3]
            close_quoation = cell_values[rx][4]
            market_situation = self.env['market.situation'].search([('code', '=', code)])
            if market_situation:
                fid = market_situation.id
                market_day_situation = self.env['market.day.situation'].search([('market_situation_id', '=', fid), ('dates', '=', dates)])
                if not market_day_situation:
                    vals = {
                            'market_situation_id': market_situation.id,
                            'dates': dates,
                            'opening_quotation': opening_quotation,
                            'close_quoation': close_quoation,
                        }
                    self.env['market.day.situation'].create(vals)

    def get_market_situation(self, b_date, e_date, transaction_date_config_id, **kwargs):
        transaction_dates = transaction_date_config_id.get_transaction_dates(b_date, e_date)
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

    _sql_constraints = [
        ('unique_dates_fund_base_data_id', 'unique (market_situation_id,dates)', '日行情日期不能重复!')
    ]
