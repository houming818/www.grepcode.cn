#!/usr/bin/env python
import os
import sys

import unittest
from django.test import Client

class HelloSquantTest(unittest.TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_hello(self):
        return
        print("\n\n")
        print("#test_001_hello.py# [start]")
        # Issue a GET request.
        #response = self.client.get('/customer/details/')

        # Check that the response is 200 OK.
        #self.assertEqual(response.status_code, 200)

        # Check that the rendered context contains 5 customers.
        print('hello squant, start testing...')

        self.assertEqual(555, 555)
        print("#test_001_hello.py# [finish]")
