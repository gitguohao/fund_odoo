# coding: utf-8
from odoo import models, fields
from extra_addons.tools import fn_timer


class NoRiskData(models.Model):
    _name = 'no.risk.data'
    _description = u'无风险数据'
    code = fields.Char(string='编码')
    name = fields.Char(string='名称')
    types = fields.Char(string='类型')
    interest_rate = fields.Float(string='收益率(%)')
    last_transaction_date = fields.Date(string='最新交易日')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='所属交易日')
    remark = fields.Char(string='备注')
    no_risk_data_lines = fields.One2many('no.risk.data.line', 'no_risk_data_id', string='无风险收益率明细')

    # @fn_timer
    def get_no_risk_data_interest_rate(self, b_date, e_date, **kwargs):
        transaction_dates = self.transaction_date_config_id.get_transaction_dates(b_date, e_date)
        interest_rates = self.env['no.risk.data.line'].search_read([
            ('transaction_date', 'in', transaction_dates),
        ], ['interest_rate'])
        interest_rates = [i['interest_rate'] for i in interest_rates]
        return interest_rates


class NoRiskDataLine(models.Model):
    _name = 'no.risk.data.line'
    _description = u'无风险收益率明细'
    transaction_date = fields.Date(string='交易日')
    interest_rate = fields.Float(string='收益率')
    no_risk_data_id = fields.Many2one('no.risk.data', string='无风险数据')
