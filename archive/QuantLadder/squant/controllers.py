
import baostock as bs

from django.db.utils import IntegrityError

from django.conf import settings

import datetime
import logging

from sq import ctx
from .baostock_sdk import BaostockContext

from .models import (
    AuInstrument, AuHistory,
    Instrument, BsHistory,
    RqInstrument
)

import squant.const as const
import squant.error as error

log = logging.getLogger(__name__)

ctx.init(
    influxdb_settings=settings.SQUANT_CONF["influxdb_settings"]
)


def get_history(
    code: str,
    frequency: str,
    start: datetime.datetime,
    end: datetime.datetime,
    source: str
):
    if settings.SQUANT_CONF["history_backend"] == "influxdb":
        df_history = ctx.Dao.get_history(code, frequency, start, end, source=source)
    else:
        raise RuntimeError(
            "history存储后端{}研发中".format(
                settings.SQUANT_CONF["history_backend"]
            )
        )
    return df_history


def get_instrument(source: str = "") -> list:
    if source not in const.ALL_SOURCE:
        raise error.SquantParamError("param source should be in {}".format(const.ALL_SOURCE))
        return None
    datas = Instrument.objects.all()
    json_dict = [{
        "code": i.code,
        "code_name": i.code_name,
        "industry": i.industry,
        "update_date": i.update_date,
        "source": i.source
    } for i in datas]
    return json_dict


def sync_instrument(source: str):
    if source == const.BS_SOURCE:
        bsctx = BaostockContext()
        json_data = bsctx.get_instrument()
        objs = []

        for i in json_data:
            objs.append(Instrument(**i))
        resp = Instrument.objects.bulk_create(objs, ignore_conflicts=True)
        cnt = len(resp)

        return cnt
    raise Exception("数据源\"{}\" not in {}".format(source, const.ALL_SOURCE))


def save_history(datas: list = []) -> int:
    # TODO 对datas做合法性校验，做预处理
    req_data = datas

    cnt = 0
    objs = []

    # MySQL后端存储history
    if settings.SQUANT_CONF['history_backend'] == "mysql":
        for i in req_data:
            objs.append(BsHistory(**i))
        try:
            cnt = BsHistory.objects.bulk_create(objs, ignore_conflicts=True)
        except IntegrityError:
            log.info("数据已存在,暂不支持变更 {} {}".format(i["code"], i["time"]))
        return cnt

    # InfluxDB后端存储history
    elif settings.SQUANT_CONF['history_backend'] == "influxdb":
        cnt = ctx.save_history(req_data)
        return cnt

    # 配置不对,没有后端存储history
    else:
        log.error(
            "SQUANT_CONF[\"history_backend\"] 配置无效，可选项[\"influxdb\", \"mysql\"]"
        )
        return -1


def sync_history(code: str, start: datetime.datetime, end: datetime.datetime, frequency: str = "", source: str = "", extras: dict = None):
    if source == "":
        raise error.SquantParamError('source 参数未指定')

    if frequency == "":
        raise error.SquantParamError('frequency 参数未指定')

    if source == const.BS_SOURCE:
        cnt = 0
        objs = []

        lg = bs.login()

        # 显示登陆返回信息
        log.info('bs.login respond error_code:' + lg.error_code)
        log.info('bs.login respond error_msg:' + lg.error_msg)

        if lg.error_code != "0":
            raise error.SquantRuntimeError("登录baostock失败")

        # 获取沪深A股历史K线数据 #
        # 详细指标参数，参见“历史行情指标参数”章节；“分钟线”参数与“日线”参数不同。“分钟线”不包含指数。
        # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
        # 周月线指标：date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg

        # TODO 判断输出是否已有历史数据 #
        # his = get_bs_histories(code, '5', start, end)
        # if len(his) > 0:
        #     log.info('had bs_save_histories {} {}'.format(i['code'], len(his)))
        #     continue

        rs = bs.query_history_k_data_plus(
            code,
            "date,time,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            frequency=frequency
        )

        if rs is None:
            raise error.SquantRuntimeError("获取bs history失败")

        log.info('bs.query_history_k_data_plus respond error_code:' + rs.error_code)
        log.info('bs.query_history_k_data_plus respond error_msg:' + rs.error_msg)

        if rs.error_code != "0":
            raise error.SquantRuntimeError("获取bs history失败")

        # 处理结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            d = dict(zip(rs.fields, rs.get_row_data()))
            d["frequency"] = frequency
            d["source"] = source
            data_list.append(d)

        if settings.SQUANT_CONF["history_backend"] == "influxdb":
            log.info(
                "写入history[code={} count={}] 到backend={} start".format(
                    code,
                    len(data_list),
                    settings.SQUANT_CONF["history_backend"]
                )
            )
            ctx.Dao.save_history(data_list)
            log.info(
                "写入history[code={} count={}] 到backend={} finish".format(
                    code,
                    len(data_list),
                    settings.SQUANT_CONF["history_backend"]
                )
            )

        elif settings.SQUANT_CONF["history_backend"] == "mysql":
            for i in data_list:
                objs.append(BsHistory(**i))
                try:
                    cnt = BsHistory.objects.bulk_create(objs, ignore_conflicts=True)
                except IntegrityError:
                    log.info("数据已存在,暂不支持变更 {} {}".format(i["code"], i["time"]))
            pass
        else:
            raise error.SquantConfigError(
                "SQUANT_CONF[\"history_backend\"] 配置无效，可选项[\"influxdb\", \"mysql\"]"
            )

        # 登出系统
        bs.logout()

    return cnt


def save_history(datas: list = []) -> int:
    if settings.SQUANT_CONF["history_backend"] == "influxdb":
        ctx.Dao.save_history(datas)
        pass
    elif settings.SQUANT_CONF["history_backend"] == "mysql":
        objs = []
        for i in datas:
            objs.append(BsHistory(**i))
            try:
                cnt = BsHistory.objects.bulk_create(objs, ignore_conflicts=True)
            except IntegrityError:
                log.info("数据已存在,暂不支持变更 {} {}".format(i["code"], i["time"]))
        pass
    else:
        raise error.SquantConfigError(
            "SQUANT_CONF[\"history_backend\"] 配置无效，可选项[\"influxdb\", \"mysql\"]"
        )

    return cnt


def AuSaveInstruments(datas):
    cnt = 0
    objs = []
    for i in datas:
        objs.append(
            AuInstrument(
                listed_date=i["listed_date"],
                delisted_date=i["delisted_date"],
                exchange=i["exchange"],
                sec_abbr=i["sec_abbr"],
                sec_name=i["sec_name"],
                symbol=i["symbol"]
            )
        )
    try:
        cnt = AuInstrument.objects.bulk_create(objs, ignore_conflicts=True)
    except IntegrityError:
        log.info("数据已存在,暂不支持变更 {}".format(i["symbol"]))
    return cnt


def AuGetInstruments():
    datas = AuInstrument.objects.all()
    json_dict = [{
        "listed_date": i.listed_date,
        "delisted_date": i.delisted_date,
        "exchange": i.exchange,
        "sec_abbr": i.sec_abbr,
        "sec_name": i.sec_name,
        "symbol": i.symbol
    } for i in datas]
    return json_dict


def AuSaveHistory(datas):
    cnt = 0
    objs = []
    for h in datas:
        objs.append(AuHistory(**h))

    try:
        cnt = AuHistory.objects.bulk_create(objs, ignore_conflicts=True)
    except IntegrityError:
        log.info("数据已存在,暂不支持变更 {}".format(i["symbol"]))
    return "saved {}".format(cnt)

def RqListInstruments():
    all_i = RqInstrument.objects.all()
    for i in all_i:
        log.info(i)
    return []

