import squant.controllers as ctrl
from .controllers import (
    AuGetInstruments, AuSaveInstruments, AuSaveHistory,
    get_instrument,
)

import datetime
from django.http import HttpResponse, JsonResponse
import json

import logging

log = logging.getLogger(__name__)


def au_save_histories(request):
    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=403)
    str_body = request.body.decode("utf-8")
    datas = json.loads(str_body)
    for i in datas:
        print(i)
    html = AuSaveHistory(datas)
    return HttpResponse("saved {}".format(html))


def au_get_instruments(request):
    data = AuGetInstruments()
    return JsonResponse(data, safe=False)


def au_save_instruments(request):
    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=403)
    str_body = request.body.decode("utf-8")
    datas = json.loads(str_body)
    for i in datas:
        i["bob"] = datetime.datetime.fromisoformat(i["bob"])
        i["eob"] = datetime.datetime.fromisoformat(i["eob"])
    html = AuSaveInstruments(datas)
    return HttpResponse("saved {}".format(html))


def get_instrument(request):
    if request.method != "GET":
        return HttpResponse("Method Not Allowed", status=403)
    datas = ctrl.get_instrument()
    return JsonResponse(datas, safe=False)


def sync_instrument(request):
    if request.method != "GET":
        return JsonResponse({"code": 405, "msg": "Method Not Allowed"}, status=403)
    # TODO 增加权限控制
    # TODO 增加不同数据源
    source = request.GET.get("source")
    if source == "":
        return JsonResponse({"code": 400, "msg": "source is required"}, status=400)
    try:
        log.info("view 发起 sync_instrument")
        count = ctrl.sync_instrument(source)
    except Exception as e:
        log.error(e)
        return JsonResponse({"code": 500, "msg": "同步数据失败"}, status=500)
    return JsonResponse({"code": 200, "msg": "同步数据 {} 条".format(count), "data": {"count": count}})


def get_history(request):
    if request.method != "GET":
        return HttpResponse("Method Not Allowed", status=403)
    code = request.GET.get("code", "")
    if code == "":
        return JsonResponse(
            {
                "code": 400,
                "msg": "code 参数未指定"
            }
        )
    frequency = request.GET.get("frequency", "5")
    start = request.GET.get("start", "2007-01-04")
    end = request.GET.get("end", "2007-01-05")
    source = request.GET.get("source", "bs")
    start = datetime.datetime.fromisoformat(start)
    end = datetime.datetime.fromisoformat(end)
    df_history = ctrl.get_history(code, frequency, start, end, source=source)
    list_resp_data = dict(zip(df_history.index, df_history.values))
    log.info("get_history {} {} count:{}".format(code, start, len(list_resp_data)))
    return JsonResponse({
        "code": 200,
        "msg": "读取history共 {} 条".format(len(list_resp_data)),
        "data": list_resp_data
    })


def save_history(request):
    # TODO 底层校验，验证底层合法性
    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=403)

    # TODO 数据合法性校验，数据预处理
    str_req_body = request.body.decode("utf-8")
    json_data = json.loads(str_req_body)
    for i in json_data:
        i["date"] = datetime.datetime.fromisoformat(i["date"])
        i["time"] = datetime.datetime.strptime(i["time"] + "+00:00", "%Y%m%d%H%M%S%f%z")
        i["code"] = i["code"]
        i["open"] = float(i["open"])
        i["high"] = float(i["high"])
        i["low"] = float(i["low"])
        i["close"] = float(i["close"])
        i["volume"] = int(i["volume"])
        i["amount"] = float(i["amount"])
        i["frequency"] = i["frequency"]
        i["source"] = i["source"]

    # TODO 开始写入history_backend
    html = ctrl.save_history(datas)
    return HttpResponse("saved {}".format(html))
