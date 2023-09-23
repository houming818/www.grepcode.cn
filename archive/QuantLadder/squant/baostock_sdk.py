import datetime
from tqdm import tqdm

import baostock as bs

import squant.error as error

import logging

from .const import BS_SOURCE

log = logging.getLogger(__name__)


class BaostockContext(object):

    def __init__(self):
        pass

    def get_instrument(self):
        # 登陆系统
        lg = bs.login()

        # 显示登陆返回信息
        log.info('login respond error_code:' + lg.error_code)
        log.info('login respond  error_msg:' + lg.error_msg)

        # 获取行业分类数据
        rs = bs.query_stock_industry()
        if rs.error_code != '0':
            log.error('bs.query_stock_industry error_code:' + rs.error_code)
            log.error('bs.query_stock_industry respond error_msg:' + rs.error_msg)
            raise error.SqantSdkError('获取baostock instrument信息失败:{}'.format(rs.error_msg))

        # 打印结果集
        list_instruments = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data = rs.get_row_data()
            list_instruments.append({
                'update_date': data[0],
                'code': data[1],
                'code_name': data[2],
                'industry': data[3],
                'source': BS_SOURCE
            })

        bs.logout()

        log.info(
            'finish bsctx.get_instrument count {}'.format(len(list_instruments))
        )

        return list_instruments

    def get_history(self, code: str, start: datetime.datetime, end: datetime.datetime, frequency: str = '5'):

        start = start.strftime('%Y-%m-%d'),
        end = end.strftime('%Y-%m-%d')

        rs = bs.query_history_k_data_plus(
            code,
            'date,time,code,open,high,low,close,volume,amount,adjustflag',
            start_date=start,
            end_date=end,
            frequency=frequency
        )
        if rs.error_code != '0':
            log.error('bs.query_stock_industry error_code:' + rs.error_code)
            log.error('bs.query_stock_industry respond error_msg:' + rs.error_msg)
            raise Exception('获取baostock history信息失败:{}'.format(rs.error_msg))

        list_history = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            list_history.append(dict(zip(rs.fields, rs.get_row_data())))

        log.info(
            'finish get_history {} {} {} count {}'.format(code, start, end, len(list_history))
        )

        # 登出系统
        bs.logout()

        return list_history
