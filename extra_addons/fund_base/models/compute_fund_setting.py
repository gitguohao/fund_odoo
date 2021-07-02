# coding: utf-8
import math
import pandas as pd
from odoo import models, fields, api, _
from datetime import date, timedelta
from extra_addons.tools import regular
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from decimal import *

n = 4
# 计算器保留位I
ipone_counter = 8


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
    risk_types = fields.Selection([('system', '系统'), ('manual', '手动')], default='system', string='选择系统/手动的RF结果')
    rm_setting_ids = fields.One2many('rm.setting', 'compute_fund_setting_id', string='选择标的', ondelete='cascade')
    fund_base_all = fields.Boolean(string='总览')
    fund_base_year = fields.Boolean(string='近一年')
    market_config_ids = fields.Many2many('market.config', string='选择标的', ondelete='restrict')
    filter_fund_base_data_ids = fields.One2many('filter.fund.base.data', 'compute_fund_setting_id', string='筛选后数据')
    year_days = fields.Integer(string='年化交易日数')
    year_weeks = fields.Integer(string='年化交易周数')
    filter_no_risk_data_line_year_ids = fields.One2many('filter.no.risk.data.line.year', 'compute_fund_setting_id', string='筛选后数据')
    filter_no_risk_data_line_month_ids = fields.One2many('filter.no.risk.data.line.month', 'compute_fund_setting_id', string='筛选后数据')
    filter_no_risk_data_line_week_ids = fields.One2many('filter.no.risk.data.line.week', 'compute_fund_setting_id', string='筛选后数据')
    filter_no_risk_data_line_day_ids = fields.One2many('filter.no.risk.data.line.day', 'compute_fund_setting_id', string='筛选后数据')
    manual_rf_ids = fields.One2many('manual.rf', 'compute_fund_setting_id', string='筛选后数据')
    rf_manual_year = fields.Float(string='自定义RF频率-年', digits=(16, 4))
    rf_manual_month = fields.Float(string='自定义RF频率-月', digits=(16, 4))
    rf_manual_week = fields.Float(string='自定义RF频率-周', digits=(16, 4))
    rf_manual_day = fields.Float(string='自定义RF频率-日', digits=(16, 4))
    filter_rm_year_ids = fields.One2many('filter.rm.year', 'compute_fund_setting_id', string='筛选后数据')
    filter_rm_month_ids = fields.One2many('filter.rm.month', 'compute_fund_setting_id', string='筛选后数据')
    filter_rm_week_ids = fields.One2many('filter.rm.week', 'compute_fund_setting_id', string='筛选后数据')
    filter_rm_day_ids = fields.One2many('filter.rm.day', 'compute_fund_setting_id', string='筛选后数据')

    _sql_constraints = [
        ('unique_code', 'unique (code)', '编码必须唯一!')
    ]

    def rm_rate(self, x, rm_name):
        if pd.isnull(x['close_quoation']) or pd.isnull(x['up_close_quoation']):
            dates = x['dates']
            notes = '{rm_name},{dates}是交易日，但没有导入收盘价!'.format(rm_name=rm_name, dates=dates)
            raise UserError(_(notes))
        # 年收益率：是（每年的最后一个交易日收盘价 / 上一年最后一个交易日的收盘价）-1 / 100
        if x['up_close_quoation']:
            r = ((x['close_quoation'] / x['up_close_quoation']) - 1)
        else:
            r = 0
        return r

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
        beg_price AS beg_price,
        end_price AS end_price,
        unit_net as unit_net,
        total_net AS total_net
        FROM
            fund_base_day_net 
        WHERE
            dates in {transaction_dates}
        """.format(transaction_dates=tuple(transaction_dates)))
        select_data_lst = self._cr.dictfetchall()

        df = pd.DataFrame(select_data_lst, columns=['fund_base_data_id', 'dates','beg_price', 'end_price', 'total_net', 'unit_net'])

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
                    beg_price = data.iloc[n]['beg_price']
                    end_price = data.iloc[n]['end_price']
                    unit_net = data.iloc[n]['unit_net']
                    total_net = data.iloc[n]['total_net']
                    filter_fund_base_day_net_d = self.env['filter.fund.base.day.net'].create({
                        'dates': dates,
                        'beg_price': beg_price,
                        'end_price': end_price,
                        'unit_net': unit_net,
                        'total_net': total_net,
                        'fund_base_data_id': filter_fund_base_data_d.id
                    })

    def rf_formula(self, x, size, times):
        a = x['rate']
        rate = math.floor(a * 10 ** n) / (10 ** n)
        years, months, weeks, dates = 0, 0, 0, ''
        if isinstance(x.name, int):
            years = x.name
        if isinstance(x.name, tuple):
            if len(x.name) == 2:
                years = x.name[0]
                months = x.name[1]
            elif len(x.name) == 3:
                years = x.name[0]
                months = x.name[1]
                weeks = x.name[2]
            elif len(x.name) == 4:
                years = x.name[0]
                months = x.name[1]
                days = x.name[3]
                dates = date.today().replace(years, months, days)
        if times == 'year':
            names = '{years}年'.format(years=years)
            self.env['filter.no.risk.data.line.year'].create({
                'name': names,
                'years': years,
                'interest_rate': rate,
                'compute_fund_setting_id': self.id
            })
        elif times == 'month':
            names = '{years}年{months}月'.format(years=years, months=months)
            self.env['filter.no.risk.data.line.month'].create({
                'name': names,
                'years': years,
                'months': months,
                'interest_rate': rate,
                'compute_fund_setting_id': self.id
            })
        elif times == 'week':
            names = '{years}年第{weeks}周'.format(years=years, weeks=weeks)
            self.env['filter.no.risk.data.line.week'].create({
                'years': years,
                'weeks': weeks,
                'name': names,
                'interest_rate': rate,
                'compute_fund_setting_id': self.id
            })
        elif times == 'day':
            self.env['filter.no.risk.data.line.day'].create({
                'dates': dates,
                'interest_rate': rate,
                'compute_fund_setting_id': self.id
            })

    def rm_formula(self, x, times):
        rate = x['rate']
        if rate:
            rate = math.floor(rate * 10 ** n) / (10 ** n)
        else:
            rate = 0
        years, months, weeks, dates = 0, 0, 0, ''
        if isinstance(x.name, int):
            years = x.name
        if isinstance(x.name, tuple):
            if len(x.name) == 2:
                years = x.name[0]
                months = x.name[1]
            elif len(x.name) == 3:
                years = x.name[0]
                months = x.name[1]
                weeks = x.name[2]
            elif len(x.name) == 4:
                years = x.name[0]
                months = x.name[1]
                days = x.name[3]
                dates = date.today().replace(years, months, days)
        if times == 'year':
            names = '{years}年'.format(years=years)
            self.env['filter.rm.year'].create({
                'name': names,
                'years': years,
                'rate': rate,
                'compute_fund_setting_id': self.id
            })
        elif times == 'month':
            names = '{years}年{months}月'.format(years=years, months=months)
            self.env['filter.rm.month'].create({
                'name': names,
                'years': years,
                'months': months,
                'rate': rate,
                'compute_fund_setting_id': self.id
            })
        elif times == 'week':
            names = '{years}年第{weeks}周'.format(years=years, weeks=weeks)
            sql = '''INSERT INTO "filter_rm_week" ("id", "years", "weeks",  "name", "rate","compute_fund_setting_id")'''
            self.env['filter.rm.week'].create({
                'years': years,
                'weeks': weeks,
                'name': names,
                'rate': rate,
                'compute_fund_setting_id': self.id
            })
        elif times == 'day':
            self.env['filter.rm.day'].create({
                'dates': dates,
                'rate': rate,
                'compute_fund_setting_id': self.id
            })

    @api.multi
    def compute_rf(self):
        self._cr.execute('delete from filter_no_risk_data_line_year where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self._cr.execute('delete from filter_no_risk_data_line_month where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self._cr.execute('delete from filter_no_risk_data_line_week where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self._cr.execute('delete from filter_no_risk_data_line_day where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self.write({'rf_manual_year': 0, 'rf_manual_month': 0, 'rf_manual_week': 0, 'rf_manual_day': 0})
        if self.risk_types == 'system':
            interest_rates = self.no_risk_data_id.get_no_risk_data_interest_rate(
                self.beg_date - timedelta(days=1), self.end_date, self.transaction_date_config_id)
            if interest_rates:
                self.get_rf_system(interest_rates)
        elif self.risk_types == 'manual':
            self.get_rf_manual()

    # 自定义RF无风险数据 time_types:频率
    def get_rf_manual(self):
        rf_manual_year = 0
        for c, rf in enumerate(self.manual_rf_ids):
            beg_date = rf.beg_date
            if c != 0:
                # 自定义RF无风险数据，不能有日期隔断
                if self.manual_rf_ids[c-1].end_date != (beg_date - timedelta(days=1)):
                    raise UserError(_('自定义RF无风险数据，不能有日期隔断!'))
            else:
                if beg_date != beg_date + relativedelta(month=1, day=1):
                    raise UserError(_('自定义RF无风险数据，开始日期必须是1月1日!'))

            end_date = rf.end_date
            days = (end_date - beg_date).days + 1
            rf_manual_year += round(Decimal(days) / 365 * Decimal(rf.interest_rate), ipone_counter)

        rf_manual_month = rf_manual_year / 12
        rf_manual_week = rf_manual_year / 52
        rf_manual_day = rf_manual_year / 365
        self.write({
            'rf_manual_year': rf_manual_year,
            'rf_manual_month': rf_manual_month,
            'rf_manual_week': rf_manual_week,
            'rf_manual_day': rf_manual_day
        })

    # 标的RF无风险数据 time_types:频率
    def get_rf_system(self, interest_rates):
        df = pd.DataFrame(interest_rates, columns=['transaction_date', 'interest_rate'])
        df['rate'] = pd.to_numeric(df['interest_rate'])
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        calendar = df['transaction_date'].dt
        # 时间维度
        times_types = ['year', 'month', 'week', 'day']
        # 创建RF不同频率的数据(年月周日)
        time_frequency_list = [getattr(calendar, 'year')]

        for times in times_types:
            # 时间频率
            if times == 'month':
                time_frequency_list.append(getattr(calendar, 'month'))
            elif times == 'week':
                china_calendar = getattr(calendar, 'isocalendar')()
                time_frequency_list.append(getattr(china_calendar, 'week'))
            elif times == 'day':
                time_frequency_list.append(getattr(calendar, 'day'))
            if self.beg_date + relativedelta(years=1) >= self.end_date and times == 'year':
                # 时间区间不到一年不算年
                continue

            elif self.beg_date + relativedelta(months=1) >= self.end_date and times == 'month':
                # 时间区间不到一月不算月
                continue
            data_group = df.groupby(time_frequency_list).mean()

            # 分组后的频率
            size = 0
            # 创建RF明细
            data_group.apply(self.rf_formula, **{'size': size, 'times': times}, axis=1)

    def rm_datas(self, beg_date, end_date, rm_id, transaction_date_config_id):
        sql = '''
        SELECT
        t.dates
        ,sum(t.close_quoation) as close_quoation
        from 
        (
        SELECT hql.dates 
        ,hql.close_quoation as close_quoation
        from market_day_situation hql
        where 
        hql.dates in (
        SELECT jyr.dates
        from transaction_date jyr 
        where 
        jyr.dates>='{beg_date}' 
        and jyr.dates <= '{end_date}' 
        and jyr.is_transaction_selection='y'
        and jyr.transaction_date_config_id={transaction_date_config_id})
        and hql.market_situation_id = {rm_id}
        union All
        SELECT jyr.dates
        ,null as close_quoation
        from transaction_date jyr 
        where 
        jyr.dates>='{beg_date}' 
        and jyr.dates <= '{end_date}' 
        and jyr.is_transaction_selection='y'
        and jyr.transaction_date_config_id={transaction_date_config_id}
        ) t
        GROUP BY t.dates
        ORDER BY t.dates 
        '''.format(beg_date=beg_date, end_date=end_date, rm_id=rm_id, transaction_date_config_id=transaction_date_config_id)
        self._cr.execute(sql)
        rm_data_lst = self._cr.dictfetchall()
        return rm_data_lst

    @api.multi
    def compute_rm(self):
        self._cr.execute(
            'delete from filter_rm_year where compute_fund_setting_id={compute_fund_setting_id}'.format(
                compute_fund_setting_id=self.id))
        self._cr.execute(
            'delete from filter_rm_month where compute_fund_setting_id={compute_fund_setting_id}'.format(
                compute_fund_setting_id=self.id))
        self._cr.execute(
            'delete from filter_rm_week where compute_fund_setting_id={compute_fund_setting_id}'.format(
                compute_fund_setting_id=self.id))
        self._cr.execute(
            'delete from filter_rm_day where compute_fund_setting_id={compute_fund_setting_id}'.format(
                compute_fund_setting_id=self.id))

        concat_df_lst = []
        for rm_setting in self.rm_setting_ids:
            rm_name = rm_setting.market_situation_id.name
            rm = rm_setting.market_situation_id
            transaction_date_config = rm.transaction_date_config_id
            rm_data_lst = self.rm_datas(str(self.beg_date - timedelta(days=1)), str(self.end_date), rm.id, transaction_date_config.id)
            up_close_quoation_lst = [rm.get('close_quoation') for rm in rm_data_lst]
            up_close_quoation_lst.insert(0, 0)
            df = pd.DataFrame(rm_data_lst, columns=['dates', 'close_quoation'])
            df['dates'] = pd.to_datetime(df['dates'])
            df['up_close_quoation'] = up_close_quoation_lst[:len(up_close_quoation_lst)-1]
            df['rate'] = df.apply(self.rm_rate, **{'rm_name': rm_name}, axis=1)
            concat_df_lst.append(df)
        concat_df = pd.concat(concat_df_lst)
        self.get_rm(concat_df)

    # 基准综合收益率 time_types:频率
    def get_rm(self, df):
        calendar = df['dates'].dt
        # 时间维度
        times_types = ['year', 'month', 'week', 'day']
        # 创建RF不同频率的数据(年月周日)

        time_frequencys = [getattr(calendar, 'year'),getattr(calendar, 'month'), getattr(calendar, 'day')]
        # 多条RM每一天的收益
        data_group = df.groupby(time_frequencys).sum()
        data_group['index'] = data_group.index
        data_group['dates'] = data_group['index'].apply(lambda x: date.today().replace(year=x[0], month=x[1], day=x[2]))
        data_group['dates'] = pd.to_datetime(data_group['dates'])

        calendar = data_group['dates'].dt
        time_frequency_list = [getattr(calendar, 'year')]
        for times in times_types:
            # 时间频率
            if times == 'month':
                time_frequency_list.append(getattr(calendar, 'month'))
            elif times == 'week':
                china_calendar = getattr(calendar, 'isocalendar')()
                time_frequency_list.append(getattr(china_calendar, 'week'))
            elif times == 'day':
                time_frequency_list.append(getattr(calendar, 'day'))

            time_datas = data_group.groupby(time_frequency_list).max()
            time_datas.apply(self.rm_formula, **{'times': times}, axis=1)



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
    beg_price = fields.Float('开盘价', digits=(16, 4))
    end_price = fields.Float('收盘价', digits=(16, 4))
    unit_net = fields.Float(string='单位净值', digits=(16, 4))
    total_net = fields.Float(string='累计净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('filter.fund.base.data', string='基金基础数据', index=True)


class FilterNoRiskDataLineDay(models.Model):
    _name = 'filter.no.risk.data.line.day'
    _description = u'筛选后的无风险收益率明细'
    dates = fields.Date('时间')
    interest_rate = fields.Float(string='日RF', digits=(16, 4))
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')
    filter_no_risk_week_id = fields.Many2one('filter.no.risk.data.line.month', string='月')


class FilterNoRiskDataLineWeek(models.Model):
    _name = 'filter.no.risk.data.line.week'
    _description = u'筛选后的无风险收益率明细'
    name = fields.Char('RF名称')
    years = fields.Integer(string='年')
    weeks = fields.Integer(string='周')
    interest_rate = fields.Float(string='周RF', digits=(16, 4))
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')
    filter_no_risk_month_id = fields.Many2one('filter.no.risk.data.line.month', string='月')
    filter_no_risk_day_ids = fields.One2many('filter.no.risk.data.line.day', 'filter_no_risk_week_id', string='日')


class FilterNoRiskDataLineMonth(models.Model):
    _name = 'filter.no.risk.data.line.month'
    _description = u'筛选后的无风险收益率明细'
    name = fields.Char('RF名称')
    years = fields.Integer(string='年')
    months = fields.Integer(string='月')
    interest_rate = fields.Float(string='月RF', digits=(16, 4))
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')
    filter_no_risk_year_id = fields.Many2one('filter.no.risk.data.line.year', string='年')
    filter_no_risk_week_ids = fields.One2many('filter.no.risk.data.line.week', 'filter_no_risk_month_id', string='周')


class FilterNoRiskDataLineYear(models.Model):
    _name = 'filter.no.risk.data.line.year'
    _description = u'筛选后的无风险收益率明细'
    name = fields.Char('RF名称')
    years = fields.Integer(string='年')
    interest_rate = fields.Float(string='年RF', digits=(16, 4))
    filter_no_risk_month_ids = fields.One2many('filter.no.risk.data.line.month', 'filter_no_risk_year_id', string='月')
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')


class manualRf(models.Model):
    _name = 'manual.rf'
    _description = u'自定义RF'
    interest_rate = fields.Float('RF值(%)', digits=(16, 4))
    beg_date = fields.Date('开始时间')
    end_date = fields.Date(string='结束时间')
    remain = fields.Char(string='备注')
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')


class FilterRmDay(models.Model):
    _name = 'filter.rm.day'
    _description = u'筛选后的大盘行情数据明细'
    dates = fields.Date('时间')
    rate = fields.Float(string='日RM', digits=(16, 4))
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')


class FilterRmWeek(models.Model):
    _name = 'filter.rm.week'
    _description = u'筛选后的大盘行情数据明细'
    name = fields.Char('RM名称')
    years = fields.Integer(string='年')
    weeks = fields.Integer(string='周')
    rate = fields.Float(string='周RM', digits=(16, 4))
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')


class FilterRmMonth(models.Model):
    _name = 'filter.rm.month'
    _description = u'筛选后的大盘行情数据明细'
    name = fields.Char('RM名称')
    years = fields.Integer(string='年')
    months = fields.Integer(string='月')
    rate = fields.Float(string='月RM', digits=(16, 4))
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')


class FilterRmYear(models.Model):
    _name = 'filter.rm.year'
    _description = u'筛选后的大盘行情数据明细'
    name = fields.Char('RM名称')
    years = fields.Integer(string='年')
    rate = fields.Float(string='年RM', digits=(16, 4))
    compute_fund_setting_id = fields.Many2one('compute.fund.setting', string='计算模型')

