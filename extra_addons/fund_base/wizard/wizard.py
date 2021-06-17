# coding: utf-8
from odoo import models, fields


class Wizard(models.TransientModel):
    _inherit = 'wizard'
    action_type = fields.Many2one('import.data.config', string=u'导入数据类型')