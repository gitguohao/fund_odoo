# coding: utf-8
import math
import pandas as pd
from odoo import models, fields, api, _
from datetime import date, timedelta
from extra_addons.tools import regular
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from decimal import *
from extra_addons.fund_base.models.logic import Logic

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

    # 刷新指标
    def refresh_indicators(self):
        times = self.time_types
        # 指标原始数据
        df = Logic().get_dataframe(self._cr, self.id)
        times_group_df = df.groupby(['fund_base_data_id'])
        rp_series = times_group_df.apply(Logic().get_rp, **{'time_types': times})
        for rp_dict in rp_series:
            fund_base_data_id = rp_dict['fund_base_data_id']
            filter_fund_base_data_vals = {
                'rp_day': rp_dict['day'].get('rp', None),
                'rp_week': rp_dict['week'].get('rp', None),
                'rp_month': rp_dict['month'].get('rp', None),
                'rp_year': rp_dict['year'].get('rp', None),
            }
            self.env['filter.fund.base.data'].browse(int(fund_base_data_id)).write(filter_fund_base_data_vals)
        return True

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
        data_ratio = (data['total_net']).sum() / data.shape[0]
        # 交易量在90%以下
        if data_ratio < 0.9:
            return False
        # year = data['dates'].dt.year
        # month = data['dates'].dt.month
        # week = data['dates'].dt.isocalendar().week
        # max_year = max(year)
        # max_month = max(month)
        # max_week = max(week)
        # g = data.groupby([year, month, week])
        # # 最后一周是否有数据
        # last_g = g.get_group((max_year, max_month, max_week))
        # if last_g['total_net'].sum() == 0:
        #     return False
        return True

    # 基金数据
    def filter_fund_datas(self, beg_date, end_date, fund_id, transaction_date_config_id):
        sql = '''
        SELECT
            dates AS dates,
            sum(beg_price) AS beg_price,
            sum(end_price) AS end_price,
            sum(unit_net) AS unit_net,
            sum(total_net) AS total_net 
        FROM
            (
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
        dates in (
        SELECT jyr.dates
        from transaction_date jyr 
        where 
        jyr.dates>='{beg_date}' 
        and jyr.dates <= '{end_date}' 
        and jyr.is_transaction_selection='y'
        and jyr.transaction_date_config_id={transaction_date_config_id}
        )
        and fund_base_data_id={fund_id}
        union All
        
        SELECT 
        jyr.transaction_date_config_id AS fund_base_data_id,
        jyr.dates AS dates,
        null AS beg_price,
        null AS end_price,
        null as unit_net,
        null AS total_net
        from transaction_date jyr 
        where 
        jyr.dates>='{beg_date}' 
        and jyr.dates <= '{end_date}' 
        and jyr.is_transaction_selection='y'
        and jyr.transaction_date_config_id={transaction_date_config_id}
        ) t
        group by t.dates
        '''.format(beg_date=beg_date, end_date=end_date, fund_id=fund_id, transaction_date_config_id=transaction_date_config_id)
        self._cr.execute(sql)
        data_lst = self._cr.dictfetchall()
        return data_lst

    def get_create_vlas(slef, df, time_types):
        keys = df.name
        years, months, weeks, dates = 0, 0, 0, False
        if isinstance(keys, int):
            years = keys
        if isinstance(keys, tuple):
            if len(keys) == 2:
                years = keys[0]
            elif len(keys) == 4:
                years = keys[0]
                months = keys[1]
                days = keys[3]
                dates = date.today().replace(years, months, days)
        if time_types == 'day':
            vlas = {
                'dates': dates,
            }

        elif time_types == 'week':
            weeks = keys[1]
            names = '{years}年第{weeks}周'.format(years=years, weeks=weeks)
            vlas = {
                'years': years,
                'weeks': weeks,
                'name': names,
            }

        elif time_types == 'month':
            months = keys[1]
            names = '{years}年第{months}月'.format(years=years, months=months)
            vlas = {
                'years': years,
                'months': months,
                'name': names,
            }
        elif time_types == 'year':
            names = '{years}年'.format(years=years)
            vlas = {
                'years': years,
                'months': months,
                'name': names,
            }
        else:
            raise UserError(_('未知的数据频率!'))
        return vlas

    def filter_create(self, x, time_types, filter_fund_id):
        total_net = x['total_net']
        vals = self.get_create_vlas(x, time_types)
        if pd.isnull(total_net):
            pass
        else:
            vals.update({'total_net': total_net})
        if time_types == 'day':
            vals.update({'fund_base_data_id': filter_fund_id})
            self.env['filter.fund.base.day.net'].create(vals)
        elif time_types == 'week':
            vals.update({'fund_base_data_id': filter_fund_id})
            self.env['filter.fund.base.week.net'].create(vals)
        elif time_types == 'month':
            vals.update({'fund_base_data_id': filter_fund_id})
            self.env['filter.fund.base.month.net'].create(vals)

    @api.multi
    def filter(self):
        self._cr.execute('delete from filter_fund_base_data where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self._cr.execute('DELETE from filter_fund_base_day_net where fund_base_data_id is null')

        fund_ids = self.env['fund.base.data'].search([])
        for fund in fund_ids:
            select_data_lst = self.filter_fund_datas(str(self.beg_date - timedelta(days=1)), str(self.end_date), fund.id, self.transaction_date_config_id.id)
            df = pd.DataFrame(select_data_lst, columns=['dates', 'total_net'])
            df['dates'] = pd.to_datetime(df['dates'])
            df['total_net'] = pd.to_numeric(df['total_net'])
            filter_bool = self.filter_workflow(df)
            if not filter_bool:
                continue
            calendar = df['dates'].dt
            filter_fund_base_data_d = self.env['filter.fund.base.data'].create({
                'fund_base_data_id': fund.id,
                'compute_fund_setting_id': self.id,
            })
            # 时间维度
            # time_types = self.time_types
            for times in ['day', 'week','month']:
                # 创建不同频率的数据(年月周日)
                time_frequency_list = [getattr(calendar, 'year')]
                if times in ['month', 'day']:
                    time_frequency_list.append(getattr(calendar, 'month'))
                if times in ['week', 'day']:
                    china_calendar = getattr(calendar, 'isocalendar')()
                    time_frequency_list.append(getattr(china_calendar, 'week'))
                if times == 'day':
                    time_frequency_list.append(getattr(calendar, 'day'))
                df_groups = df.groupby(time_frequency_list).sum()

                filter_fund_id= filter_fund_base_data_d.id
                df_groups.apply(self.filter_create, **{'time_types': times, 'filter_fund_id': filter_fund_id}, axis=1)
        return True

    def rf_formula(self, x, size, times):
        vals = self.get_create_vlas(x, times)
        rate = x['rate']

        if pd.isnull(rate):
            pass
        else:
            rate = math.floor(rate * 10 ** n) / (10 ** n)
            vals.update({'interest_rate': rate})
        if times == 'year':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.no.risk.data.line.year'].create(vals)
        elif times == 'month':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.no.risk.data.line.month'].create(vals)
        elif times == 'week':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.no.risk.data.line.week'].create(vals)
        elif times == 'day':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.no.risk.data.line.day'].create(vals)

    def rm_formula(self, x, times):
        vals = self.get_create_vlas(x, times)
        rate = x['rate']
        if pd.isnull(rate):
            pass
        else:
            rate = math.floor(rate * 10 ** n) / (10 ** n)
            vals.update({'rate': rate})
        if times == 'year':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.rm.year'].create(vals)
        elif times == 'month':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.rm.month'].create(vals)
        elif times == 'week':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.rm.week'].create(vals)
        elif times == 'day':
            vals.update({'compute_fund_setting_id': self.id})
            self.env['filter.rm.day'].create(vals)

    @api.multi
    def compute_rf(self):
        self._cr.execute('delete from filter_no_risk_data_line_year where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self._cr.execute('delete from filter_no_risk_data_line_month where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self._cr.execute('delete from filter_no_risk_data_line_week where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self._cr.execute('delete from filter_no_risk_data_line_day where compute_fund_setting_id={compute_fund_setting_id}'.format(compute_fund_setting_id=self.id))
        self.write({'rf_manual_year': 0, 'rf_manual_month': 0, 'rf_manual_week': 0, 'rf_manual_day': 0})
        if self.risk_types == 'system':
            beg_date = self.beg_date - timedelta(days=1)
            datas = self.rf_datas(beg_date, self.end_date, self.no_risk_data_id.id, self.transaction_date_config_id.id)
            if datas:
                self.get_rf_system(datas)
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
        df = pd.DataFrame(interest_rates, columns=['dates', 'rate'])
        df['rate'] = pd.to_numeric(df['rate'])
        df['dates'] = pd.to_datetime(df['dates'])
        calendar = df['dates'].dt
        # 时间维度
        times_types = ['year', 'month', 'week', 'day']
        # 创建RF不同频率的数据(年月周日)
        for times in times_types:
            time_frequency_list = [getattr(calendar, 'year')]
            # 时间频率
            if times in ['month', 'day'] and times != 'week':
                time_frequency_list.append(getattr(calendar, 'month'))
            if times in ['week', 'day']:
                china_calendar = getattr(calendar, 'isocalendar')()
                time_frequency_list.append(getattr(china_calendar, 'week'))
            if times == 'day':
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

    def rf_datas(self, beg_date, end_date, rf_id, transaction_date_config_id):
        sql = '''
        SELECT
        t.dates
        ,sum(t.rate) as rate
        from 
        (
        SELECT r.transaction_date  as dates
        ,r.interest_rate  as rate
        from no_risk_data_line r
        where 
        r.transaction_date in (
        SELECT jyr.dates
        from transaction_date jyr 
        where 
        jyr.dates>='{beg_date}' 
        and jyr.dates <= '{end_date}' 
        and jyr.is_transaction_selection='y'
        and jyr.transaction_date_config_id={transaction_date_config_id})
        and r.no_risk_data_id = {rf_id}
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
        '''.format(beg_date=beg_date, end_date=end_date, rf_id=rf_id, transaction_date_config_id=transaction_date_config_id)
        self._cr.execute(sql)
        data_lst = self._cr.dictfetchall()
        return data_lst

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
        transaction_date_config_id = self.transaction_date_config_id.id

        concat_df_lst = []
        for rm_setting in self.rm_setting_ids:
            rm_name = rm_setting.market_situation_id.name
            rm = rm_setting.market_situation_id
            rm_data_lst = self.rm_datas(str(self.beg_date - timedelta(days=1)), str(self.end_date), rm.id, transaction_date_config_id)
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
        for times in times_types:
            time_frequency_list = [getattr(calendar, 'year')]
            # 时间频率
            if times in ['month', 'day']:
                time_frequency_list.append(getattr(calendar, 'month'))
            if times in ['week', 'day']:
                china_calendar = getattr(calendar, 'isocalendar')()
                time_frequency_list.append(getattr(china_calendar, 'week'))
            if times == 'day':
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
    filter_fund_base_week_net_ids = fields.One2many('filter.fund.base.week.net', 'fund_base_data_id', string='日净值')
    filter_fund_base_month_net_ids = fields.One2many('filter.fund.base.month.net', 'fund_base_data_id', string='日净值')
    time_types = fields.Selection(related='compute_fund_setting_id.time_types', readonly=True, store=True)
    total_std = fields.Float(string='总览-标准差', digits=(16, 4))
    year_std = fields.Float(string='近一年-标准差', digits=(16, 4))
    market_std = fields.Float(string='熊市-标准差', digits=(16, 4))
    rp_day = fields.Float(string='RP几何平均日化收益', digits=(16, 4))
    rp_week = fields.Float(string='RP几何平均周化收益', digits=(16, 4))
    rp_month = fields.Float(string='RP几何平均月化收益', digits=(16, 4))
    rp_year = fields.Float(string='RP几何平均年化收益', digits=(16, 4))


class FilterFundBaseDayNet(models.Model):
    _name = 'filter.fund.base.day.net'
    _description = u'筛选后的日净值'
    dates = fields.Date('时间')
    beg_price = fields.Float('开盘价', digits=(16, 4))
    end_price = fields.Float('收盘价', digits=(16, 4))
    unit_net = fields.Float(string='单位净值', digits=(16, 4))
    total_net = fields.Float(string='累计净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('filter.fund.base.data', string='筛选后的日净值', index=True)


class FilterFundBaseWeekNet(models.Model):
    _name = 'filter.fund.base.week.net'
    _description = u'筛选后的周净值'
    name = fields.Char('RF名称')
    years = fields.Integer(string='年')
    weeks = fields.Integer(string='周')
    total_net = fields.Float(string='累计净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('filter.fund.base.data', string='筛选后的周净值', index=True)


class FilterFundBaseMonthNet(models.Model):
    _name = 'filter.fund.base.month.net'
    _description = u'筛选后的月净值'
    name = fields.Char('RF名称')
    years = fields.Integer(string='年')
    months = fields.Integer(string='月')
    total_net = fields.Float(string='累计净值', digits=(16, 4))
    fund_base_data_id = fields.Many2one('filter.fund.base.data', string='筛选后的月净值', index=True)


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

