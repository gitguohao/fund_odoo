# coding: utf-8
import math
import pandas as pd
from odoo import models, fields, api
from datetime import date

n = 4


class ComputeFundSetting(models.Model):
    _name = "compute.fund.setting"
    _description = u'计算模型设置'
    code = fields.Char(string='模型编码')
    name = fields.Char(string='模型名称')
    time_types = fields.Selection([('day', '天'), ('week', '周'), ('month', '月')], string='时间维度')
    transaction_date_config_id = fields.Many2one('transaction.date.config', string='交易日')
    beg_date = fields.Date(string='开始时间')
    end_date = fields.Date(string='结束时间', default=date.today())
    last_compute_indicators_datetime = fields.Datetime(string='最新指标计算时间')
    no_risk_data_id = fields.Many2one('no.risk.data', string='选择标的')
    system_no_risk_data_rate = fields.Float(string='系统计算RF结果', digits=(16, 4))
    manual_no_risk_data_rate = fields.Float(string='手动计算RF结果', digits=(16, 4))
    risk_types = fields.Selection([('system', '系统'), ('manual', '手动')], default='system', string='选择系统/手动的RF结果')
    rm_setting_ids = fields.One2many('rm.setting', 'compute_fund_setting_id', string='选择标的')
    rm_rate = fields.Float(string='基准综合收益率', digits=(16, 4))
    fund_base_all = fields.Boolean(string='总览')
    fund_base_year = fields.Boolean(string='近一年')
    market_config_ids = fields.Many2many('market.config', string='选择标的')
    filter_fund_base_data_ids = fields.One2many('filter.fund.base.data', 'compute_fund_setting_id', string='筛选后数据')

    @api.multi
    def filter(self):
        pass

    def rf_formula(self, x, size):
        a = (1 / size) * x['interest_rate']
        math.floor(a * 10 ** n) / (10 ** n)
        return a

    # 无风险数据 time_types:频率
    def get_rf(self, interest_rates, time_types):
        df = pd.DataFrame(interest_rates, columns=['interest_rate', 'transaction_date'])
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        china_calendar = df['transaction_date'].dt
        if time_types == 'week':
            china_calendar = getattr(china_calendar, 'isocalendar')()
        times = getattr(china_calendar, time_types)
        data_group = df.groupby(times).max()
        size = data_group.index.size
        # group后添加行
        data_group['formula_value'] = data_group.apply(self.rf_formula, size=size, axis=1)
        return data_group

    # 基准综合收益率 time_types:频率
    def get_rm(self, market_situation_items, time_types):
        df = pd.DataFrame(market_situation_items, columns=['close_quoation', 'dates'])
        df['dates'] = pd.to_datetime(df['dates'])
        if time_types != 'day':
            china_calendar = df['dates'].dt
            if time_types == 'week':
                china_calendar = getattr(china_calendar, 'isocalendar')()
            times = getattr(china_calendar, time_types)
            data_group = df.groupby(times).max()
            df.sort_values(by=['dates'])
        else:
            data_group = df
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
            interest_rates = self.no_risk_data_id.get_no_risk_data_interest_rate(self.beg_date, self.end_date)
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
                market_situation_items = rm_setting.market_situation_id.get_market_situation(self.beg_date, self.end_date)
                if market_situation_items:
                    rm_rate += self.get_rm(market_situation_items, self.time_types) * (rm_setting.ratio * 0.01)
            rm_rate = math.floor(rm_rate * 10 ** n) / (10 ** n)
        self.rm_rate = rm_rate


class RmSetting(models.Model):
    _name = "rm.setting"
    _description = u'设置基准收益率'
    market_situation_id = fields.Many2one('market.situation', string='选择指数')
    ratio = fields.Integer('占比(%)')
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='选择标的')


class FilterFundBaseData(models.Model):
    _name = "filter.fund.base.data"
    _description = u'筛选后的基金基础数据'
    fund_base_data_id = fields.Many2one('fund.base.data', string='名称')
    code = fields.Char(related='fund_base_data_id.code', string='编码')
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='选择标的')
    filter_fund_base_day_net_ids = fields.One2many('filter.fund.base.day.net', 'fund_base_data_id', string='日净值')


class FilterFundBaseDayNet(models.Model):
    _name = 'filter.fund.base.day.net'
    _description = u'筛选后的日净值'
    dates = fields.Date('时间')
    unit_net = fields.Float(string='单位净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('filter.fund.base.data', string='基金基础数据', index=True)


