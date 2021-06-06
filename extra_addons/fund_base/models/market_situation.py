# coding: utf-8
import xlrd
import math
import base64
from odoo.exceptions import UserError
from odoo import models, fields, _
from extra_addons.tools import regular


class MarketSituation(models.Model):
    _name = 'market.situation'
    _description = u'大盘行情数据'
    code = fields.Char(string='指数代码', regular=regular, tips='编码只能输入字母或汉字!')
    name = fields.Char(string='指数名称')
    opening_quotation = fields.Float(string='最新开盘点位', compute='compute_market_day_situation_id')
    close_quoation = fields.Float(string='最新收盘点位', compute='compute_market_day_situation_id')
    last_transaction_date = fields.Date(string='最新交易日', compute='compute_market_day_situation_id')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='所属交易日', ondelete='restrict')
    remark = fields.Char(string='备注')
    market_day_situation_ids = fields.One2many('market.day.situation', 'market_situation_id', string='日行情')

    _sql_constraints = [
        ('unique_code', 'unique (code)', '编码必须唯一!')
    ]

    def compute_market_day_situation_id(self):
        for rec in self:
            market_day_situation_vals = rec.get_market_day_situation_id()
            if market_day_situation_vals:
                rec.opening_quotation = str(market_day_situation_vals.get('opening_quotation', ''))
                rec.close_quoation = market_day_situation_vals.get('close_quoation', '')
                rec.last_transaction_date = str(market_day_situation_vals.get('dates', ''))

    def get_market_day_situation_id(self):
        sql = '''
        select n.dates as dates
        , n.opening_quotation as opening_quotation
        , n.close_quoation as close_quoation
        from market_day_situation n
        where n.market_situation_id={market_situation_id}
        and (close_quoation != 0)
        order by n.dates desc limit 1
        '''.format(market_situation_id=self.id)
        self._cr.execute(sql)
        res = self._cr.dictfetchone()
        vals = {}
        if res:
            vals.update(res)
        return vals

    def import_data(self, data):
        excel = xlrd.open_workbook(file_contents=base64.decodestring(data))
        sh = excel.sheet_by_index(0)
        cell_values = sh._cell_values
        success_c = 0
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
        num = sh.nrows - 1
        notes = '共导入{num}条数据,成功导入{success_c}条,失败{fail_c}'.format(num=num, success_c=success_c, fail_c=(num-success_c))
        return notes

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
    interest_rate = fields.Float(string='日收益率', digits=(16, 4), compute='compute_interest_rate')
    market_situation_id = fields.Many2one('market.situation', string='大盘行情数据')

    _sql_constraints = [
        ('unique_dates_fund_base_data_id', 'unique (market_situation_id,dates)', '日行情日期不能重复!')
    ]

    def compute_interest_rate(self):
        for rec in self:
            interest_rate = 0
            if rec.close_quoation != 0:
                interest_rate = rec.get_interest_rate()
            interest_rate = math.floor(interest_rate * 10 ** 4) / (10 ** 4)
            rec.interest_rate = interest_rate

    def get_interest_rate(self):
        transaction_date_config = self.market_situation_id.transaction_date_config_id
        transaction_dates = self.env['transaction.date'].search([
            ('transaction_date_config_id', '=', transaction_date_config.id),
            ('dates', '<=', self.dates),
            ('is_transaction_selection', '=', 'y')
        ], order='dates desc', limit=2)
        if len(transaction_dates) == 2:
            # 当天行情
            d = self.search([
                ('dates', '=', transaction_dates[0].dates),
                ('market_situation_id', '=', self.market_situation_id.id),
                ('close_quoation', '!=', 0)
            ], limit=1)

            # 上一天的
            d_1 = self.search([
                ('dates', '=', transaction_dates[1].dates),
                ('market_situation_id', '=', self.market_situation_id.id),
                ('close_quoation', '!=', 0)
            ], order='dates desc', limit=1)
            if d and d_1:
                interest_rate = (d.close_quoation / d_1.close_quoation) - 1
            elif d:
                interest_rate = 0
            else:
                interest_rate = 0
        else:
            interest_rate = 0
        return interest_rate

    def check(self, vals):
        if 'close_quoation' in vals:
            if vals['close_quoation'] != 0:
                raise UserError(_(u'收盘点位不能等于0'))

    def create(self, vals_list):
        self.check(vals_list)
        return super(MarketDaySituation, self).create(vals_list)

    def wirte(self, vals):
        self.check(vals)
        return super(MarketDaySituation, self).wirte(vals)