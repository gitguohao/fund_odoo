# coding: utf-8
import math
import pandas as pd
from odoo import models, fields, api
from datetime import date, timedelta
import xlrd
import base64
from extra_addons.tools import regular

n = 4


class ComputeFundSetting(models.Model):
    _name = "compute.fund.setting"
    _description = u'计算模型设置'
    code = fields.Char(string='模型编码', regular=regular, tips='编码只能输入字母或汉字!')
    name = fields.Char(string='模型名称')
    time_types = fields.Selection([('day', '天'), ('week', '周'), ('month', '月')], string='时间维度')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='交易日', ondelete='cascade')
    beg_date = fields.Date(string='开始时间')
    end_date = fields.Date(string='结束时间', default=date.today())
    last_compute_indicators_datetime = fields.Datetime(string='最新指标计算时间')
    no_risk_data_id = fields.Many2one('no.risk.data', string='选择标的', ondelete='restrict')
    system_no_risk_data_rate = fields.Float(string='系统计算RF结果', digits=(16, 4))
    manual_no_risk_data_rate = fields.Float(string='手动计算RF结果', digits=(16, 4))
    risk_types = fields.Selection([('system', '系统'), ('manual', '手动')], default='system', string='选择系统/手动的RF结果')
    rm_setting_ids = fields.One2many('rm.setting', 'compute_fund_setting_id', string='选择标的', ondelete='cascade')
    rm_rate = fields.Float(string='基准综合收益率', digits=(16, 4))
    fund_base_all = fields.Boolean(string='总览')
    fund_base_year = fields.Boolean(string='近一年')
    market_config_ids = fields.Many2many('market.config', string='选择标的', ondelete='restrict')
    filter_fund_base_data_ids = fields.One2many('filter.fund.base.data', 'compute_fund_setting_id', string='筛选后数据')

    _sql_constraints = [
        ('unique_code', 'unique (code)', '编码必须唯一!')
    ]
    def import_data(self, data):
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
            # 日期
            dates = cell_values[rx][2]
            # 开盘价
            beg_price = cell_values[rx][3]
            # 收盘价
            end_price = cell_values[rx][4]
            # 单位净值
            unit_net = cell_values[rx][5]
            # 累计净值
            total_net = cell_values[rx][6]
            fund_base_data = self.env['fund.base.data'].search([('code', '=', code)])
            if fund_base_data:
                fid = fund_base_data.id
                fund_base_day_net = self.env['fund.base.day.net'].search([('fund_base_data_id', '=', fid), ('dates', '=', dates)])
                if not fund_base_day_net:
                    vals = {
                            'fund_base_data_id': fund_base_data.id,
                            'dates': dates,
                            'total_net': total_net,
                            'beg_price': beg_price,
                            'end_price': end_price,
                            'unit_net': unit_net,
                        }
                    success_c += 1
                    self.env['fund.base.day.net'].create(vals)
        num = sh.nrows - 1
        notes = '共导入{num}条数据,成功导入{success_c}条,失败{fail_c}'.format(num=num, success_c=success_c, fail_c=(num-success_c))
        return notes

    def filter_workflow(self, data):
        data_ratio = (data['total_net'] != 0).sum() / data.shape[0]
        # 交易量在90%以下
        if data_ratio < 0.9:
            return False
        year = data['dates'].dt.year
        month = data['dates'].dt.month
        week = data['dates'].dt.isocalendar().week
        max_year = max(year)
        max_month = max(month)
        max_week = max(week)
        g = data.groupby([year, month, week])
        # 最后一周是否有数据
        last_g = g.get_group((max_year, max_month, max_week))
        if last_g['total_net'].sum() == 0:
            return False
        return True

    @api.multi
    def filter(self):
        self._cr.execute('delete from filter_fund_base_data where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        transaction_dates = self.transaction_date_config_id.get_transaction_dates(self.beg_date, self.end_date)
        transaction_dates = [str(d) for d in transaction_dates]
        self._cr.execute("""
        SELECT
        fund_base_data_id AS fund_base_data_id,
        dates AS dates,
        total_net AS total_net,
        unit_net as unit_net
        FROM
            fund_base_day_net 
        WHERE
            dates in {transaction_dates}
        """.format(transaction_dates=tuple(transaction_dates)))
        select_data_lst = self._cr.dictfetchall()

        df = pd.DataFrame(select_data_lst, columns=['fund_base_data_id', 'dates', 'total_net', 'unit_net'])

        df['dates'] = pd.to_datetime(df['dates'])
        df['total_net'] = pd.to_numeric(df['total_net'])
        df_groups = df.groupby('fund_base_data_id')
        for fund_base_data_id, data in df_groups:
            filter_bool = self.filter_workflow(data)
            # 总览标准差
            total_std = data['total_net'].std(ddof=0)
            if filter_bool:
                filter_fund_base_data_d = self.env['filter.fund.base.data'].create({
                    'fund_base_data_id': fund_base_data_id,
                    'compute_fund_setting_id': self.id,
                    'total_std': total_std
                })
                for n in range(0, data.shape[0]):
                    dates = data.iloc[n]['dates']
                    unit_net = data.iloc[n]['unit_net']
                    filter_fund_base_day_net_d = self.env['filter.fund.base.day.net'].create({
                        'dates': dates,
                        'unit_net': unit_net,
                        'fund_base_data_id': filter_fund_base_data_d.id
                    })

    def rf_formula(self, x, size):
        a = (1 / size) * x['interest_rate']
        math.floor(a * 10 ** n) / (10 ** n)
        return a

    # 无风险数据 time_types:频率
    def get_rf(self, interest_rates, time_types):
        df = pd.DataFrame(interest_rates, columns=['interest_rate', 'transaction_date'])
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        calendar = df['transaction_date'].dt
        # 时间频率
        time_frequency_list = [getattr(calendar, 'year')]
        if time_types in ['month', 'week', 'day']:
            time_frequency_list.append(getattr(calendar, 'month'))
        if time_types in ['month', 'week']:
            china_calendar = getattr(calendar, 'isocalendar')()
            time_frequency_list.append(getattr(china_calendar, 'week'))
        if time_types == 'day':
            time_frequency_list.append(getattr(calendar, 'day'))
        data_group = df.groupby(time_frequency_list).max()
        size = data_group.index.size
        # group后添加行
        data_group['formula_value'] = data_group.apply(self.rf_formula, size=size, axis=1)
        return data_group

    # 基准综合收益率 time_types:频率
    def get_rm(self, market_situation_items, time_types):
        df = pd.DataFrame(market_situation_items, columns=['close_quoation', 'dates'])
        df['dates'] = pd.to_datetime(df['dates'])
        calendar = df['dates'].dt
        # 时间频率
        time_frequency_list = [getattr(calendar, 'year')]
        if time_types in ['month', 'week', 'day']:
            time_frequency_list.append(getattr(calendar, 'month'))
        if time_types in ['month', 'week']:
            china_calendar = getattr(calendar, 'isocalendar')()
            time_frequency_list.append(getattr(china_calendar, 'week'))
        if time_types == 'day':
            time_frequency_list.append(getattr(calendar, 'day'))
        data_group = df.groupby(time_frequency_list).max()
        size = data_group.index.size
        b, c = data_group.iloc[0]['close_quoation'], data_group.iloc[size - 1]['close_quoation']
        # RM单个标的收益
        rm_profit = (c / b) - 1
        return rm_profit

    # 系统计算RF结果/系统计算无风险收益率计算
    @api.onchange('no_risk_data_id', 'beg_date', 'end_date', 'time_types')
    def onchange_interest_rates(self):
        system_no_risk_data_rate = 0
        if self.no_risk_data_id and self.beg_date and self.end_date and self.time_types:
            interest_rates = self.no_risk_data_id.get_no_risk_data_interest_rate(self.beg_date - timedelta(days=1), self.end_date, self.transaction_date_config_id)
            rates_sum = 0
            if interest_rates:
                rfs = self.get_rf(interest_rates, self.time_types)
                rates_sum = rfs['formula_value'].sum()
            system_no_risk_data_rate = math.floor(rates_sum * 10 ** n) / (10 ** n)
        self.system_no_risk_data_rate = system_no_risk_data_rate

    @api.onchange('rm_setting_ids', 'beg_date', 'end_date', 'time_types')
    def onchange_rm_rate(self):
        rm_rate = 0
        if self.rm_setting_ids and self.beg_date and self.end_date and self.time_types:
            rm_rate = 0
            for rm_setting in self.rm_setting_ids:
                market_situation_items = rm_setting.market_situation_id.get_market_situation(self.beg_date - timedelta(days=1), self.end_date, self.transaction_date_config_id)
                if market_situation_items:
                    rm_rate += self.get_rm(market_situation_items, self.time_types) * (rm_setting.ratio * 0.01)
            rm_rate = math.floor(rm_rate * 10 ** n) / (10 ** n)
        self.rm_rate = rm_rate


class RmSetting(models.Model):
    _name = "rm.setting"
    _description = u'设置基准收益率'
    market_situation_id = fields.Many2one('market.situation', string='选择指数', ondelete='restrict')
    ratio = fields.Integer('占比(%)')
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')


class FilterFundBaseData(models.Model):
    _name = "filter.fund.base.data"
    _description = u'筛选后的基金基础数据'
    fund_base_data_id = fields.Many2one('fund.base.data', string='名称')
    code = fields.Char(related='fund_base_data_id.code', string='编码')
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')
    filter_fund_base_day_net_ids = fields.One2many('filter.fund.base.day.net', 'fund_base_data_id', string='日净值')
    total_std = fields.Float(string='总览-标准差', digits=(16, 4))
    year_std = fields.Float(string='近一年-标准差', digits=(16, 4))
    market_std = fields.Float(string='熊市-标准差', digits=(16, 4))


class FilterFundBaseDayNet(models.Model):
    _name = 'filter.fund.base.day.net'
    _description = u'筛选后的日净值'
    dates = fields.Date('时间')
    unit_net = fields.Float(string='单位净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('filter.fund.base.data', string='基金基础数据', index=True)

#
# class FundBaseIndicators(models.Model):
#     _name = 'fund.base.indicators'
#     _description = u'基金指标'
#     fund_base_data_id = fields.Many2one('filter.fund.base.data', string='基金基础数据', index=True)

