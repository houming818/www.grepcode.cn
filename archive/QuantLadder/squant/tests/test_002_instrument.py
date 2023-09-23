#!/usr/bin/env python

import squant.const as const
import squant.controllers as ctrl
# import tests.error as error

import json

import unittest
from django.test import Client


import time


class InstrumentTest(unittest.TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_runner(self):
        return
        print("\n\n")
        print("#test_002_instrument.py# [start]")
        time.sleep(1)
        print("\n")
        self.sync_instrument_by_ctrl()
        print("\n")
        time.sleep(5)
        self.sync_instrument_by_curl()
        print("#test_002_instrument.py# [finish]")

    def sync_instrument_by_ctrl(self):
        print("#sync_instrument_by_ctrl# [doing]")
        source = const.BS_SOURCE
        cnt = ctrl.sync_instrument(source=source)
        print("get data")
        print("获取BsInstrucment 总共\"{}\"条".format(cnt))
        print("#sync_instrument_by_ctrl# [done]")

    def sync_instrument_by_curl(self):
        print("#sync_instrument_by_curl# [doing]")
        source = const.BS_SOURCE
        resp = self.client.get('/api/v1/sync_instrument/', {
            "source": source
        })
        print("get data")
        print(resp.content)
        json_resp = json.loads(resp.content)
        print(json_resp)
        # Check that the response is 200 OK.
        if json_resp["code"] != 200:
            print("获取Instrucment Fail")
        else:
            print("获取Instrucment 总共\"{}\"条".format(json_resp["data"]["count"]))
        print("#sync_instrument_by_curl# [done]")
