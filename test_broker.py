
import os
import platform
import sys
from time import sleep

import py_ctp.ctp_struct as ctp
from py_ctp.ctp_quote import Quote
from py_ctp.ctp_trade import Trade

import _thread
import QUANTAXIS as QA
from QUANTAXIS.QAMarket.QABroker import QA_Broker

sys.path.append(QA.QASetting.QALocalize.bin_path)  # 调用QA_Binpath下的dll


class QA_ATBroker(QA_Broker):
    def __init__(self, front_td, front_md, broker, investor='008107', pwd='1'):

        self.req = 0
        self.ordered = False
        self.needAuth = False
        self.RelogEnable = True
        self.broker = broker
        self.investor = investor
        self.pwd = pwd

        self.prepare()

        self.t.OnFrontConnected = self.OnFrontConnected
        self.t.OnFrontDisconnected = self.OnFrontDisconnected
        self.t.OnRspUserLogin = self.OnRspUserLogin
        self.t.OnRspSettlementInfoConfirm = self.OnRspSettlementInfoConfirm
        self.t.OnRspAuthenticate = self.OnRspAuthenticate
        self.t.OnRtnInstrumentStatus = self.OnRtnInstrumentStatus
        self.t.OnRspOrderInsert = self.OnRspOrderInsert
        self.t.OnRtnOrder = self.OnRtnOrder

    def prepare(self):
        self.con_path = '{}{}{}'.format(
            QA.QASetting.QALocalize.cache_path, os.sep, 'at_ctp')
        os.makedirs(self.con_path, exist_ok=True)

        self.trade_con_path = '{}{}{}'.format(
            self.con_path, os.sep, self.investor)
        os.makedirs(self.trade_con_path, exist_ok=True)

        self.dllpath = os.path.join(
            QA.QASetting.QALocalize.bin_path, 'py_ctp_at')

        self.q = Quote(os.path.join(self.dllpath, 'ctp_quote.' +
                                    ('dll' if 'Windows' in platform.system() else 'so')))
        self.t = Trade(os.path.join(self.dllpath, 'ctp_trade.' +
                                    ('dll' if 'Windows' in platform.system() else 'so')))

        self.t.CreateApi(self.trade_con_path)
        spi = self.t.CreateSpi()
        self.t.RegisterSpi(spi)

    def q_OnFrontConnected(self):
        print('connected')
        self.login()

    def OnFrontConnected(self):
        if not self.RelogEnable:
            return
        print('connected')
        if self.needAuth:
            self.t.ReqAuthenticate(
                self.broker, self.investor, '@haifeng', '8MTL59FK1QGLKQW2')
        else:
            self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor,
                                Password=self.pwd, UserProductInfo='@haifeng')

    def OnFrontDisconnected(self, reason: int):
        print(reason)

    def OnRspAuthenticate(self, pRspAuthenticateField: ctp.CThostFtdcRspAuthenticateField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        print('auth：{0}:{1}'.format(
            pRspInfo.getErrorID(), pRspInfo.getErrorMsg()))
        self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor,
                            Password=self.pwd, UserProductInfo='@haifeng')

    def OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        print(info.getErrorMsg())

        if info.getErrorID() == 0:
            self.Session = rsp.getSessionID()
            self.t.ReqSettlementInfoConfirm(
                BrokerID=self.broker, InvestorID=self.investor)
        else:
            self.RelogEnable = False

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm: ctp.CThostFtdcSettlementInfoConfirmField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        # print(pSettlementInfoConfirm)
        _thread.start_new_thread(self.StartQuote, ())

    def q_OnTick(self, tick: ctp.CThostFtdcMarketDataField):
        f = tick
        # print(tick)

        if not self.ordered:
            _thread.start_new_thread(self.Order, (f,))
            self.ordered = True

    def Order(self, f: ctp.CThostFtdcMarketDataField):
        print("报单")
        self.req += 1
        self.t.ReqOrderInsert(
            BrokerID=self.broker,
            InvestorID=self.investor,
            InstrumentID=f.getInstrumentID(),
            OrderRef='{0:>12}'.format(self.req),
            UserID=self.investor,
            OrderPriceType=ctp.OrderPriceTypeType.LimitPrice,
            Direction=ctp.DirectionType.Buy,
            CombOffsetFlag=ctp.OffsetFlagType.Open.__char__(),
            CombHedgeFlag=ctp.HedgeFlagType.Speculation.__char__(),
            LimitPrice=f.getLastPrice() - 50,
            VolumeTotalOriginal=1,
            TimeCondition=ctp.TimeConditionType.GFD,
            # GTDDate=''
            VolumeCondition=ctp.VolumeConditionType.AV,
            MinVolume=1,
            ContingentCondition=ctp.ContingentConditionType.Immediately,
            StopPrice=0,
            ForceCloseReason=ctp.ForceCloseReasonType.NotForceClose,
            IsAutoSuspend=0,
            IsSwapOrder=0,
            UserForceClose=0)

    def login(self):
        self.q.ReqUserLogin(BrokerID=self.broker,
                            UserID=self.investor, Password=self.pwd)

    def OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        print(info.getErrorMsg())

        if info.getErrorID() == 0:
            self.Session = rsp.getSessionID()
            self.t.ReqSettlementInfoConfirm(
                BrokerID=self.broker, InvestorID=self.investor)
        else:
            self.RelogEnable = False

    def query_orders(self):
        pass

    def query_deal(self):
        pass

    def query_positions(self):
        pass

    def receive_order(self):
        pass

    def run(self):
        self.investor = '008107'
        self.pwd = '1'
