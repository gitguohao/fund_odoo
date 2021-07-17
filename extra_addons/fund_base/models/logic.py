# coding: utf-8
from extra_addons.postgres_connect_test import selectOperate
from extra_addons.tools import get_time_frequency_list
import pandas as pd


class Logic(object):
    # 获取RP
    def get_rp(self, x, time_types):
        '''
        :param x:
        :return indicators_list:
        '''
        fund_base_data_id = x.name
        # 开始时间累计净值
        b_total_net = x.loc[x['total_net'].last_valid_index()]['total_net']
        b_total_net = b_total_net and b_total_net or 1
        # 结束时间累计净值
        e_total_net = x.loc[x['total_net'].first_valid_index()]['total_net']
        # 基金/总收益率
        total_profit = (e_total_net / b_total_net) - 1

        calendar = x['dates'].dt
        time_frequency_list = get_time_frequency_list(calendar, time_types)
        # 开始时间/结束时间 有效频率数
        valid_x = x.dropna(inplace=False)
        valid_groups = valid_x.groupby(time_frequency_list)
        valid_num = valid_groups.ngroups

        # 总交易频率数
        time_types_num = 0

        # 第一次保证主频率
        times = ['year', 'month', 'week', 'day']
        time_types_index = times.index(time_types)
        times[time_types_index], times[0] = times[0], times[time_types_index]
        vals = {
            'fund_base_data_id': fund_base_data_id,
        }
        for types in times:
            # 开始时间/结束时间 全部频率数
            time_frequency_list = get_time_frequency_list(calendar, types)
            df_groups = x.groupby(time_frequency_list)
            # 总交易频率数
            num = df_groups.ngroups
            if types == time_types:
                time_types_num = num
            # rp = (（1+总收益率-基金） ^ X) - 1
            # X =（开始时间/结束时间 频率数 / 总交易频率数(types)） / 总交易频率数
            xx = (valid_num / num) / time_types_num
            rp = ((1 + total_profit) ** xx) - 1
            vals.update({
                types: {},
            })
            vals[types].update({'rp': rp})
        return vals

    # 指标原始数据
    def get_dataframe(self, cr, cid):
        '''
        :param times: 频率
        :return:
        '''
        sql = "select fund_net.fund_base_data_id,fund_net.total_net,fund_net.dates " \
              " from filter_fund_base_day_net fund_net" \
              " left join filter_fund_base_data fund on fund_net.fund_base_data_id=fund.id" \
              " where fund.compute_fund_setting_id={cid}".format(cid=cid)
        cr.execute(sql)
        datas = cr.dictfetchall()
        columns = ['fund_base_data_id', 'total_net', 'dates']
        df = pd.DataFrame(datas, columns=columns).sort_values('dates', ascending=False, inplace=False)
        # 使用删除NaN值的方式处理数据，默认删除的就是行的数据，如果包含NaN就直接删除这一行数据，可以指定当前的axis
        # df = df.dropna(inplace=False)
        df['total_net'] = df[['total_net']].apply(pd.to_numeric)
        df['fund_base_data_id'] = df['fund_base_data_id'].astype("int")
        df['dates'] = pd.to_datetime(df['dates'])
        return df


class LogicTest(object):
    # 指标原始数据
    def get_dataframe(self, times):
        '''
        :param times: 频率
        :return:
        '''
        # times_list = []
        # if times == 'day':
        #     sql = "select fund_base_data_id,total_net,dates from filter_fund_base_day_net"
        #     times_list.append('dates')
        # elif times == 'weeks':
        #     sql = "select fund_base_data_id,total_net,years,weeks from filter_fund_base_week_net"
        #     times_list.extend(['years', 'weeks'])
        # elif times == 'month':
        #     sql = "select fund_base_data_id,total_net,years,months from filter_fund_base_month_net"
        #     times_list.extend(['years', 'months'])
        # else:
        #     return ValueError('RP频率未设定')
        sql = "select fund_base_data_id,total_net,dates from filter_fund_base_day_net"

        datas = selectOperate(sql)
        columns = ['fund_base_data_id', 'total_net', 'dates']
        df = pd.DataFrame(datas, columns=columns).sort_values('dates', ascending=False, inplace=False)
        # 使用删除NaN值的方式处理数据，默认删除的就是行的数据，如果包含NaN就直接删除这一行数据，可以指定当前的axis
        # df = df.dropna(inplace=False)
        df['total_net'] = df[['total_net']].apply(pd.to_numeric)
        df['fund_base_data_id'] = df['fund_base_data_id'].astype("int")
        df['dates'] = pd.to_datetime(df['dates'])
        return df
#
# total_profit = None
# , 'weeks', 'month'
# for times in ['weeks']:
#     # sql = ''
#     # times_list = []
#     # if times == 'day':
#     #     sql = "select fund_base_data_id,total_net,dates from filter_fund_base_day_net"
#     # elif times == 'weeks':
#     #     sql = "select fund_base_data_id,total_net,dates,years,weeks from filter_fund_base_week_net"
#     #     times_list.extend(['years', 'weeks'])
#     # elif times == 'month':
#     #     sql = "select fund_base_data_id,total_net,dates,years,months from filter_fund_base_month_net"
#     #     times_list.extend(['years', 'months'])
#     sql = "select fund_base_data_id,total_net,dates from filter_fund_base_day_net"
#
#     datas = selectOperate(sql)
#
#     columns = ['fund_base_data_id', 'total_net', 'dates']
#     # columns.extend(times_list)
#     df = pd.DataFrame(datas, columns=columns).sort_values(['dates'], ascending=False, inplace=False)
#     # 使用删除NaN值的方式处理数据，默认删除的就是行的数据，如果包含NaN就直接删除这一行数据，可以指定当前的axis
#     # df = df.dropna(inplace=False)
#     df['total_net'] = df[['total_net']].apply(pd.to_numeric)
#     df['dates'] = pd.to_datetime(df['dates'])
#     times_group_df = df.groupby(['fund_base_data_id'])
#
#     t = times_group_df.apply(Logic().get_rp)
#     for i in t:
#         print(i)
