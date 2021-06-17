# coding: utf-8
from odoo import models, fields


class ImportDataConfig(models.Model):
    _name = 'import.data.config'
    name = fields.Char('名称')
    model_id = fields.Many2one('ir.model', string='模型')
    field_name = fields.Many2one('ir.model.fields', string='字段', domain="[('model_id', '=', model_id)]", help='选择记录后,将把数据导入到这个字段上')