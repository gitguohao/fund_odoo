# coding: utf-8
from odoo.exceptions import UserError
from odoo import models, fields, _


class Wizard(models.TransientModel):
    _name = 'wizard'
    years_keys = list(range(2000, 2029))
    years_values = list(range(2000, 2029))
    years_tuple = zip(years_keys, years_values)
    years_selection = list(years_tuple)

    years = fields.Selection(years_selection, '年')
    binary_data = fields.Binary(string='选择文件', attachment=True)

    def action_import_create(self):
        action_types = self._context.get('types', '')

        if action_types == 'fund_title':
            notes = self.env['fund.base.data'].import_fund_title_data(self.binary_data)
        elif action_types == 'fund_base_data':
            notes = self.env['fund.base.data'].import_fund_base_data(self.binary_data)
        elif action_types == 'market_situation':
            notes = self.env['market.situation'].import_data(self.binary_data)
        else:
            notes = '导入失败,未定义导入类型,请联系管理员!'
        self._cr.commit()
        raise UserError(_(notes))

    # act_create_wizard 用于创建记录
    # act_refresh_wizard 用于刷新记录
    # def act_create_wizard(self):
    #     active_model = self._context.get('active_model')
    #     active_ids = self._context.get('active_ids')
    #     self.env[active_model].browse(active_ids).create_transaction_date({'years': self.years})