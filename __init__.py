# coding:utf-8

import QUANTAXIS as QA

from py_ctp import test_trade

import time
tt = test_trade.TestTrade()
# t.OnConnected = t.ReqUserLogin('008105', '1', '9999')
# t.ReqConnect('tcp://180.168.146.187:10000')
tt.run()

time.sleep(6)
for inst in tt.t.instruments.values():
    print(inst)
input()
tt.release()