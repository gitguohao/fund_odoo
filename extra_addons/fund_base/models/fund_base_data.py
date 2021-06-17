# coding: utf-8
import xlrd
import base64
from odoo import models, fields
from extra_addons.tools import regular
import pandas as pd


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

    def create_data(self, df, types, model_name, filed):
        code = df.name
        fund_base_data = self.env['fund.base.data'].search([('code', '=', code)])
        success_rows = 0
        if fund_base_data:
            fid = fund_base_data.id
            for date, value in df.items():
                fund_base_day_net = self.env[model_name].search([
                    ('fund_base_data_id', '=', fid), ('dates', '=', date)
                ])
                if not fund_base_day_net:
                    fund_base_day_net.create({
                        'fund_base_data_id': fid,
                        'dates': date,
                        filed: value
                    })
                else:
                    fund_base_day_net.write({filed: value})
                success_rows += 1
        return success_rows

    def import_fund_base_data(self, data, types):
        debase_data = base64.b64decode(data)
        df_dicts = pd.read_excel(debase_data, sheet_name=None, index_col=0)
        sheets = list(df_dicts.keys())
        df = df_dicts.get(sheets[0])
        model_name = types.model_id.model
        filed = types.field_name
        success_rows = 0
        total_rows = df.shape[0]
        success_rows += df.apply(types, model_name, filed)
        notes = '共导入{total_rows}条数据,成功导入{success_rows}条,失败{fail_rows}'.format(total_rows=total_rows, success_rows=success_rows, fail_rows=(total_rows - success_rows))
        return notes

    def import_fund_title_data(self, data):
        excel = xlrd.open_workbook(file_contents=base64.decodestring(data))
        sh = excel.sheet_by_index(0)
        cell_values = sh._cell_values
        success_c = 0
        for rx in range(sh.nrows):
            if rx == 0: continue
            # 编码
            code = cell_values[rx][0]
            # 名称
            name = cell_values[rx][1]
            # 类型
            types = cell_values[rx][2]
            # 成立日期
            dates = cell_values[rx][3]
            # 基金经理人
            fund_manager = cell_values[rx][4]
            # 管理人
            manager = cell_values[rx][5]
            # 备注1
            x1 = cell_values[rx][6]
            # 备注2
            x2 = cell_values[rx][7]
            # 备注3
            x3 = cell_values[rx][8]
            # 备注4
            x4 = cell_values[rx][9]
            # 备注5
            x5 = cell_values[rx][10]
            # 备注6
            x6 = cell_values[rx][11]
            # 备注7
            x7 = cell_values[rx][12]
            # 备注8
            x8 = cell_values[rx][13]
            # 备注9
            x9 = cell_values[rx][14]
            # 备注10
            x10 = cell_values[rx][15]

            fund_base_data = self.env['fund.base.data'].search([('code', '=', code)])
            if not fund_base_data:
                vals = {
                        'code': code,
                        'name': name,
                        'types': types,
                        'establish_date': dates,
                        'fund_manager': fund_manager,
                        'manager': manager,
                        'x1': x1,
                        'x2': x2,
                        'x3': x3,
                        'x4': x4,
                        'x5': x5,
                        'x6': x6,
                        'x7': x7,
                        'x8': x8,
                        'x9': x9,
                        'x10': x10,
                    }
                success_c += 1
                self.env['fund.base.data'].create(vals)
        num = sh.nrows - 1
        notes = '共导入{num}条数据,成功导入{success_c}条,失败{fail_c}'.format(num=num, success_c=success_c, fail_c=(num-success_c))
        return notes

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

