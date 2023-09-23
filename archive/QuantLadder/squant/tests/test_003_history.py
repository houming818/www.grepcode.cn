#!/usr/bin/env python

import squant.const as const

import os
import sys
import datetime
import json

from tqdm import tqdm

import unittest
from django.test import Client

import squant.controllers as ctrl
from django.conf import settings

import time


class HistoryTest(unittest.TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_runner(self):
        print("\n\n")
        print("#test_003_history.py# [start]")
        time.sleep(1)
        print("\n")
#        self.sync_history_by_ctrl()
        print("\n")
#        self.sync_history_by_curl()
        print("\n")
        self.get_history_by_ctrl()
        print("\n")
        self.get_history_by_curl()
        print("#test_003_history.py# [finish]")

    def sync_history_by_ctrl(self):
        print("#sync_history_by_ctrl# [doing]")
        source = const.BS_SOURCE
        list_instrument = ctrl.get_instrument(const.BS_SOURCE)
        start = datetime.datetime.fromisoformat("2001-01-01T00:00:00+00:00")
        end = datetime.datetime.fromisoformat("2022-01-01T00:00:00+00:00")
        frequency = "5"
        source = const.BS_SOURCE

        target = [
            {
                "code": ins["code"],
                "start": start,
                "end": end
            }
            for ins in list_instrument
        ]

        last_range = settings.SQUANT_CONF["test"]["last_range"]
        target = target[:last_range]

        list_history = None
        for i in tqdm(target, postfix="\n"):
            list_history = ctrl.sync_history(
                i["code"], i["start"], i["end"], frequency, source
            )
        print("get data")
        print(list_history)
        print("#sync_history_by_ctrl# [done]")

    def sync_history_by_curl(self):
        print("#sync_history_by_curl# [doing]")
        source = const.BS_SOURCE
        list_instrument = ctrl.get_instrument(const.BS_SOURCE)
        start = datetime.datetime.fromisoformat("2001-01-01T00:00:00+00:00")
        end = datetime.datetime.fromisoformat("2022-01-01T00:00:00+00:00")
        frequency = "5"
        source = const.BS_SOURCE

        target = [
            {
                "code": ins["code"],
                "start": start,
                "end": end
            }
            for ins in list_instrument
        ]

        last_range = settings.SQUANT_CONF["test"]["last_range"]
        target = target[:last_range]

        list_history = None
        for i in tqdm(target, postfix="\n"):
            list_history = ctrl.sync_history(
                i["code"], i["start"], i["end"], frequency, source
            )
        print("get data")
        print(list_history)
        print("#sync_history_by_curl# [done]")

    def get_history_by_ctrl(self):
        print("#get_history_by_ctrl# [doing]")
        list_instrument = ctrl.get_instrument(const.BS_SOURCE)
        start = datetime.datetime.fromisoformat("2020-01-01T00:00:00+00:00")
        end = datetime.datetime.fromisoformat("2020-01-15T00:00:00+00:00")

        target = [
            {
                "code": i['code'],
                "start": start,
                "end": end
            }
            for i in list_instrument[:settings.SQUANT_CONF["test"]["last_range"]]
        ]

        list_history = None
        for i in target:
            list_history = ctrl.get_history(
                i["code"], "5", i["start"], i["end"], const.BS_SOURCE
            )
            print("get data {} {}->{} count: {}".format(i["code"], start, end, len(list_history)))
        print("#get_history_by_ctrl# [done]")

    def get_history_by_curl(self):
        print("#get_history_by_curl# [doing]")

        list_instrument = ctrl.get_instrument(const.BS_SOURCE)
        start = datetime.datetime.fromisoformat("2020-01-01T00:00:00+00:00")
        end = datetime.datetime.fromisoformat("2020-01-15T00:00:00+00:00")

        target = [
            {
                "code": i['code'],
                "start": start,
                "end": end
            }
            for i in list_instrument[:settings.SQUANT_CONF["test"]["last_range"]]
        ]

        for t in target:
            resp = self.client.get(
                "/api/v1/get_history/",
                {
                    "code": t["code"],
                    "frequency": "5",
                    "start": t["start"],
                    "end": t["end"],
                    "source": const.BS_SOURCE
                }
            )
            json_resp = json.loads(resp.content.decode("utf-8"))
            print(
                "get data {} {}->{} count: {}".format(
                    t["code"],
                    start,
                    end,
                    len(json_resp["data"])
                )
            )
            print(json_resp["data"])
            self.assertEqual(json_resp["code"], 200)

        # Check that the response is 200 OK.
#        print(json.loads(response.content))
print("#get_bs_history from curl# [done]")
