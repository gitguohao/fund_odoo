# coding: utf-8
from odoo import models, fields, api, _
from extra_addons.tools import Tools
from odoo.exceptions import UserError
from extra_addons.tools import fn_timer


class TransactionDateConfig(models.Model):
    _name = 'transaction.date.config'
    _description = u'交易日管理'
    name = fields.Char('名称')
    code = fields.Char('编码')
    remark = fields.Char('备注')
    transaction_date_year_ids = fields.One2many('transaction.date.year', 'transaction_date_config_id',string='交易日配置')

    # 获取交易日
    # @fn_timer
    def get_transaction_dates(self, b_date, e_date, **kwargs):
        transaction_dates = self.env['transaction.date'].search_read([
            ('transaction_date_config_id', '=', self.id),
            ('dates', '>=', b_date),
            ('dates', '<=', e_date),
            ('is_transaction_selection', '=', 'y')
        ], ["dates"])
        transaction_dates = [transaction['dates'] for transaction in transaction_dates]
        return transaction_dates


class TransactionDateYear(models.Model):
    _name = 'transaction.date.year'
    _description = u'交易日-年'
    years_keys = list(range(2000, 2029))
    years_values = list(range(2000, 2029))
    years_tuple = zip(years_keys, years_values)
    years_selection = list(years_tuple)

    years = fields.Selection(years_selection, '年')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='交易日配置')
    transaction_date_ids = fields.One2many('transaction.date', 'transaction_date_year_id',string='交易日配置')

    def create_transaction_date(self, kwargs):
        vals = {'dates': ''}
        allDayPerYear = Tools().getAllDayPerYear(kwargs['years'])
        for rec in self:
            for day in allDayPerYear:
                vals['dates'] = day
                vals['transaction_date_config_id'] = rec.transaction_date_config_id.id
                vals['transaction_date_year_id'] = rec.id
                self.env['transaction.date'].create(vals)

    @api.model
    def create(self, vals):
        transactiondateyear = super(TransactionDateYear, self).create(vals)
        transactiondateyear.create_transaction_date(vals)
        return transactiondateyear

    def write(self, vals):
        if 'years' in vals:
            raise UserError(_('交易日年份,年份不可以修改'))
        return super(TransactionDateYear, self).write(vals)


class TransactionDate(models.Model):
    _name = 'transaction.date'
    _description = u'交易日'
    dates = fields.Date('日期')
    is_transaction_selection = fields.Selection([('y', '是'),('n', '否')], string='是否交易日')
    transaction_date_year_id = fields.Many2one('transaction.date.year', string='交易日配置-年')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='交易日配置')
