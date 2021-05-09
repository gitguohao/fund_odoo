# coding: utf-8
from odoo import models, fields


class TransactionDateConfig(models.Model):
    _name = 'transaction.date.config'
    _description = u'交易日管理'
    name = fields.Char('名称')
    code = fields.Char('编码')
    remark = fields.Char('备注')
    transaction_date_ids = fields.One2many('transaction.date', 'transaction_date_config_id',string='交易日配置')


class TransactionDate(models.Model):
    _name = 'transaction.date'
    _description = u'交易日'
    dates = fields.Date('日期')
    is_transaction_selection = fields.Selection([('y', '是'),('n', '否')], string='是否交易日')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='交易日配置')
