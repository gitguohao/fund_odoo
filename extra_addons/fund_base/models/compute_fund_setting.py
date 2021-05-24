# coding: utf-8
import math
import pandas as pd
from odoo import models, fields, api
from datetime import date
from extra_addons.tools import fn_timer


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
    manual_no_risk_data_rate = fields.Float(string='手动计算RF结果')
    risk_types = fields.Selection([('system', '系统'), ('manual', '手动')], default='system', string='选择系统/手动的RF结果')
    rm_setting_ids = fields.One2many('rm.setting', 'compute_fund_setting_id', string='选择标的')
    fund_base_all = fields.Boolean(string='总览')
    fund_base_year = fields.Boolean(string='近一年')
    market_config_ids = fields.Many2many('market.config', string='选择标的')
    filter_fund_base_data_ids = fields.One2many('filter.fund.base.data', 'compute_fund_setting_id', string='筛选后数据')

    # 无风险数据(周)
    def rf_weeks(self, interest_rates):
        df = pd.DataFrame(interest_rates, columns=['interest_rate', 'transaction_date'])
        week_groups = df.groupby([df['transaction_date'].dt.isocalendar().week]).max()
        return week_groups

    # 系统计算RF结果/系统计算无风险收益率计算
    # @fn_timer
    @api.onchange('no_risk_data_id', 'beg_date', 'end_date')
    def onchange_interest_rates(self):
        if self.no_risk_data_id and self.beg_date and self.end_date and self.time_types:
            interest_rates = self.no_risk_data_id.get_no_risk_data_interest_rate(self.beg_date, self.end_date)
            if self.time_types == 'day':
                interest_rates_len = len(interest_rates)
                rf_interest_rates = [interest_rate * (1/interest_rates_len) for interest_rate in interest_rates]
                n = 4
                rates_sum = sum(rf_interest_rates)
                system_no_risk_data_rate = math.floor(rates_sum * 10 ** n) / (10 ** n)
            elif self.time_types == 'week':
                rf_weeks = self.rf_weeks(interest_rates)
                # 多少周
                rf_weeks.index.size
                system_no_risk_data_rate = 0

            else:
                system_no_risk_data_rate = 0
        else:
            system_no_risk_data_rate = 0
        self.system_no_risk_data_rate = system_no_risk_data_rate


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


