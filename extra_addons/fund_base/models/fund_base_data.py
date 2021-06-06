# coding: utf-8
from odoo import models, fields
from extra_addons.tools import regular


class FundBaseData(models.Model):
    _name = 'fund.base.data'
    _description = u'基金基础数据'
    code = fields.Char(string='编码', regular=regular, tips='编码只能输入字母或汉字!')
    name = fields.Char(string='名称')
    last_price = fields.Float(string='最新现价', digits=(16, 4), compute='compute_fund_base_day_net_id')
    last_price_date = fields.Date(string='最新现价时间', compute='compute_fund_base_day_net_id')
    unit_net = fields.Float(string='单位净值', digits=(16, 4), compute='compute_fund_base_day_net_id')
    total_net = fields.Float(string='累计净值', digits=(16, 4), compute='compute_fund_base_day_net_id')
    types = fields.Char(string='类型')
    establish_date = fields.Date(string='成立日')
    fund_manager = fields.Char(string='基金经理人')
    manager = fields.Char(string='管理人')
    fund_base_day_net_ids = fields.One2many('fund.base.day.net', 'fund_base_data_id', string='日净值')
    fund_base_day_net_id = fields.Many2one('fund.base.day.net', string='日净值')
    x1 = fields.Char(string='自定义1')
    x2 = fields.Char(string='自定义2')
    x3 = fields.Char(string='自定义3')
    x4 = fields.Char(string='自定义4')
    x5 = fields.Char(string='自定义5')
    x6 = fields.Char(string='自定义6')
    x7 = fields.Char(string='自定义7')
    x8 = fields.Char(string='自定义8')
    x9 = fields.Char(string='自定义9')
    x10 = fields.Char(string='自定义10')

    def compute_fund_base_day_net_id(self):
        for rec in self:
            fund_base_data = rec.get_fund_base_day_net_id()
            if fund_base_data:
                rec.last_price_date = str(fund_base_data.get('dates', ''))
                rec.last_price = fund_base_data.get('last_price', '')
                rec.unit_net = fund_base_data.get('unit_net', '')
                rec.total_net = fund_base_data.get('total_net', '')

    def get_fund_base_day_net_id(self):
        sql = '''
        select n.id as fund_base_day_net_id
        , n.dates as dates
        , n.end_price as last_price
        , n.unit_net as unit_net
        , n.total_net as total_net
        from fund_base_day_net n
        where n.fund_base_data_id={fund_base_data_id}
        and (end_price != 0 or unit_net!=0 or total_net!=0)
        order by n.dates desc limit 1
        '''.format(fund_base_data_id=self.id)
        self._cr.execute(sql)
        res = self._cr.dictfetchone()
        vals = {}
        if res:
            vals.update(res)
        return vals

    # def write(self, vals):
    #     if 'fund_base_day_net_ids' in vals:
    #         # 写入日净值
    #         super(FundBaseData, self).write({'fund_base_day_net_ids': vals['fund_base_day_net_ids']})
    #         del vals['fund_base_day_net_ids']
    #
    #         # 获取最后日净值记录
    #         fund_base_day_net_vals = self.get_fund_base_day_net_id()
    #         rid = fund_base_day_net_vals.get('fund_base_day_net_id', 0)
    #
    #         if not self.fund_base_day_net_id or self.fund_base_day_net_id.id != rid:
    #             vals.update(fund_base_day_net_vals)
    #     return super(FundBaseData, self).write(vals)


class FundBaseDayNet(models.Model):
    _name = 'fund.base.day.net'
    _description = u'日净值'
    dates = fields.Date('时间', index=True)
    beg_price = fields.Float('开盘价', digits=(16, 4))
    end_price = fields.Float('收盘价', digits=(16, 4))
    unit_net = fields.Float(string='单位净值', digits=(16, 4))
    total_net = fields.Float(string='累计净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('fund.base.data', string='基金基础数据', index=True)

    _sql_constraints = [
        ('unique_dates_fund_base_data_id', 'unique (fund_base_data_id,dates)', '日净值日期不能重复!')
    ]

