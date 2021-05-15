# coding: utf-8
from odoo import models, fields


class Wizard(models.TransientModel):
    _name = 'wizard'
    years_keys = list(range(2000, 2029))
    years_values = list(range(2000, 2029))
    years_tuple = zip(years_keys, years_values)
    years_selection = list(years_tuple)

    years = fields.Selection(years_selection, '年')
    # act_create_wizard 用于创建记录
    # act_refresh_wizard 用于刷新记录
    def act_create_wizard(self):
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        self.env[active_model].browse(active_ids).create_transaction_date({'years': self.years})