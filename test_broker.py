
from time import sleep
import _thread
import QUANTAXIS as QA
from QUANTAXIS.QAMarket.QABroker import QA_Broker
from py_ctp.ctp_trade import Trade
from py_ctp.ctp_quote import Quote
import py_ctp.ctp_struct as ctp
import sys
import os
import platform
sys.path.append(QA.QASetting.QALocalize.bin_path)  # 调用QA_Binpath下的dll



class QA_ATBroker(QA_Broker):
    def __init__(self):
        pass