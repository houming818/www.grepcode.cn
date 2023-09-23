import json, requests, datetime
from tqdm import tqdm
import baostock as bs
import pandas as pd
from django.core.serializers.json import DjangoJSONEncoder
from .controllers import BsGetInstruments, BsSaveHistories

import random

import logging

log = logging.getLogger(__name__)


def sync_bs_histories():
    bs.login()
    instruments = get_bs_instruments()
#    random.shuffle(instruments)
    base = datetime.datetime.today()
    def gdate():
        for i in instruments:
            for n in range(0, 365*20, 365):
                yield {
            'code': i['code'],
            'start': (base - datetime.timedelta(days=n)).strftime('%Y-%m-%d'),
            'end': (base - datetime.timedelta(days=(n-365))).strftime('%Y-%m-%d')
        }
    for i in tqdm(gdate(), total=len(instruments)*20):
        code = i['code']
        start = i['start']
        end = i['end']
        rs = bs.query_history_k_data_plus(
            code,
            "date,time,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start,
            end_date=end,
            frequency="5", adjustflag="3"
        )
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(dict(zip(rs.fields, rs.get_row_data())))

        print("sync_history {} {} {} {}".format(code, start, end, len(data_list)))
        BsSaveHistories(data_list)

    # 登出系统
    bs.logout()


def update_bs_instruments_from_source():
    # 登陆系统
    lg = bs.login()
    # 显示登陆返回信息
    log.info('login respond error_code:' + lg.error_code)
    log.info('login respond  error_msg:' + lg.error_msg)

    # 获取行业分类数据
    rs = bs.query_stock_industry()
    # rs = bs.query_stock_basic(code_name="浦发银行")
    log.info('query_stock_industry error_code:' + rs.error_code)
    log.info('query_stock_industry respond  error_msg:' + rs.error_msg)

    # 打印结果集
    industry_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data = rs.get_row_data()
        industry_list.append({
            "update_date": data[0],
            "code": data[1],
            "code_name": data[2],
            "industry": data[3]
        })
    #result = pd.DataFrame(industry_list, columns=rs.fields)
    # 结果集输出到csv文件
    #result.to_csv("D:/stock_industry.csv", encoding="gbk", index=False)
    req_data = json.dumps(industry_list, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    resp = requests.post('http://192.168.1.102:5556/api/v1/bs/save_instruments/', data=req_data)
    log.info('finish bs_save_instruments {}'.format(resp.content.decode('utf-8')))

    # 登出系统
    bs.logout()


def update_bs_history_from_source():
    # 登陆系统
    lg = bs.login()
    # 显示登陆返回信息
    log.info('login respond error_code:' + lg.error_code)
    log.info('login respond  error_msg:' + lg.error_msg)

    #### 获取沪深A股历史K线数据 ####
    # 详细指标参数，参见“历史行情指标参数”章节；“分钟线”参数与“日线”参数不同。“分钟线”不包含指数。
    # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
    # 周月线指标：date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg
    instruments = get_bs_instruments()
    random.shuffle(instruments)
    base = datetime.datetime.today()
    target = [
        {
            'code': i['code'],
            'start': (base - datetime.timedelta(days=365 * n)).strftime('%Y-%m-%d'),
            'end': (base - datetime.timedelta(days=365 * (n-1))).strftime('%Y-%m-%d')
        }
        for i in instruments
        for n in range(0, 20)
    ]
    for i in tqdm(target):
        code = i['code']
        start = i['start']
        end = i['end']
        his = get_bs_histories(code, '5', start, end)
        if len(his) > 0:
            log.info('had bs_save_histories {} {}'.format(i['code'], len(his)))
            continue
        rs = bs.query_history_k_data_plus(
            code,
            "date,time,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start, end_date=end,
            frequency="5", adjustflag="3"
        )
        log.info('query_history_k_data_plus respond error_code:' + rs.error_code)
        log.info('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

        #### 打印结果集 ####
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(dict(zip(rs.fields, rs.get_row_data())))

        # 打印结果集
        #result = pd.DataFrame(industry_list, columns=rs.fields)
        # 结果集输出到csv文件
        #result.to_csv("D:/stock_industry.csv", encoding="gbk", index=False)
        req_data = json.dumps(data_list, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        resp = requests.post('http://192.168.1.102:5556/api/v1/bs/save_histories/', data=req_data)
        log.info('finish bs_save_histories {} {}'.format(i['code'], resp.content.decode('utf-8')))

    # 登出系统
    bs.logout()


def get_bs_instruments():
    resp = requests.get('http://192.168.1.102:5556/api/v1/bs/get_instruments/')
    resp_json = json.loads(resp.content)
    log.info('finish get_bs_instruments {}'.format(len(resp_json)))
    return resp_json


def get_bs_histories(code, frequency, start, end):
    resp = requests.get('http://192.168.1.102:5556/api/v1/bs/get_histories/', params={
        "code": code,
        "frequency": frequency,
        "start": start,
        "end": end
    })
    resp_json = json.loads(resp.content)
    log.info('requested get_bs_history {} {} {} {}'.format(code, start, end, len(resp_json)))
    return resp_json

