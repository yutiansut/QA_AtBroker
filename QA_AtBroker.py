
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
    def __init__(self,   investor='008107', pwd='1', broker='9999', front_md='tcp://180.168.146.187:10031', front_td='tcp://180.168.146.187:10030'):

        self.req = 0
        self.ordered = False
        self.needAuth = False
        self.RelogEnable = True
        self.broker = broker
        self.investor = investor
        self.pwd = pwd
        self.front_md = front_md
        self.front_td = front_td
        self.prepare()

    def prepare(self):
        """创建 trade/quote 

        1. dll load
        2. 实例化
        3. 回调函数句柄替换
        """

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
        t_spi = self.t.CreateSpi()
        self.t.RegisterSpi(t_spi)
        self.q.CreateApi(self.con_path)
        q_spi = self.q.CreateSpi()
        self.q.RegisterSpi(q_spi)

        self.t.OnFrontConnected = self.OnFrontConnected
        self.t.OnFrontDisconnected = self.OnFrontDisconnected
        self.t.OnRspUserLogin = self.OnRspUserLogin
        self.t.OnRspSettlementInfoConfirm = self.OnRspSettlementInfoConfirm
        self.t.OnRspAuthenticate = self.OnRspAuthenticate
        self.t.OnRtnInstrumentStatus = self.OnRtnInstrumentStatus
        self.t.OnRspOrderInsert = self.OnRspOrderInsert
        self.t.OnRtnOrder = self.OnRtnOrder

        self.q.OnFrontConnected = self.q_OnFrontConnected
        self.q.OnRspUserLogin = self.q_OnRspUserLogin
        self.q.OnRtnDepthMarketData = self.q_OnTick

        self.t.RegCB()
        self.q.RegCB()

    def q_OnFrontConnected(self):
        print('connected')
        self.login()

    def q_OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        print(info)
        self.q.SubscribeMarketData('rb1901')

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

    def OnRtnInstrumentStatus(self, pInstrumentStatus: ctp.CThostFtdcInstrumentStatusField):
        print(pInstrumentStatus.getInstrumentStatus())

    def OnRspOrderInsert(self, pInputOrder: ctp.CThostFtdcInputOrderField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        print(pRspInfo)
        print(pInputOrder)
        print(pRspInfo.getErrorMsg())

    def OnRtnOrder(self, pOrder: ctp.CThostFtdcOrderField):
        print(pOrder)
        # if pOrder.getSessionID() == self.Session and pOrder.getOrderStatus() == ctp.OrderStatusType.NoTradeQueueing:
        #     print("撤单")
        #     self.t.ReqOrderAction(
        #         self.broker, self.investor,
        #         InstrumentID=pOrder.getInstrumentID(),
        #         OrderRef=pOrder.getOrderRef(),
        #         FrontID=pOrder.getFrontID(),
        #         SessionID=pOrder.getSessionID(),
        #         ActionFlag=ctp.ActionFlagType.Delete)

    def q_OnTick(self, tick: ctp.CThostFtdcMarketDataField):
        f = tick
        print(tick)
        """
        TradingDay = '20181113', InstrumentID = 'rb1901', ExchangeID = '', 
        ExchangeInstID = '', LastPrice = 3878.0, PreSettlementPrice = 3869.0, PreClosePrice = 3848.0, 
        PreOpenInterest = 2500080.0, OpenPrice = 3850.0, HighestPrice = 3895.0, LowestPrice = 3835.0, 
        Volume = 2100784, Turnover = 81223915140.0, OpenInterest = 2450594.0, ClosePrice = 1.7976931348623157e+308, 
        SettlementPrice = 1.7976931348623157e+308, UpperLimitPrice = 4139.0, LowerLimitPrice = 3598.0, 
        PreDelta = 0.0, CurrDelta = 1.7976931348623157e+308, UpdateTime = '04:05:21', UpdateMillisec = 500,
        BidPrice1 = 3877.0, BidVolume1 = 506, AskPrice1 = 3878.0, AskVolume1 = 228, 
        BidPrice2 = 1.7976931348623157e+308, BidVolume2 = 0, AskPrice2 = 1.7976931348623157e+308, AskVolume2 = 0,
        BidPrice3 = 1.7976931348623157e+308, BidVolume3 = 0, AskPrice3 = 1.7976931348623157e+308, AskVolume3 = 0, 
        BidPrice4 = 1.7976931348623157e+308, BidVolume4 = 0, AskPrice4 = 1.7976931348623157e+308, AskVolume4 = 0, 
        BidPrice5 = 1.7976931348623157e+308, BidVolume5 = 0, AskPrice5 = 1.7976931348623157e+308, AskVolume5 = 0, 
        AveragePrice = 38663.62041028492, ActionDay = '20181113'
        """


        if not self.ordered:
            _thread.start_new_thread(self.Order, (f,))
            self.ordered = True

    def StartQuote(self):
        self.q.CreateApi(self.con_path)
        spi = self.q.CreateSpi()
        self.q.RegisterSpi(spi)

        self.q.OnFrontConnected = self.q_OnFrontConnected
        self.q.OnRspUserLogin = self.q_OnRspUserLogin
        self.q.OnRtnDepthMarketData = self.q_OnTick

        self.q.RegCB()

        self.q.RegisterFront(self.front_md)
        self.q.Init()
        # self.q.Join()

    def Qry(self):
        sleep(1.1)
        self.t.ReqQryInstrument()
        while True:
            sleep(1.1)
            self.t.ReqQryTradingAccount(self.broker, self.investor)
            sleep(1.1)
            self.t.ReqQryInvestorPosition(self.broker, self.investor)
            return

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

    def query_orders(self):
        pass

    def query_deal(self):
        pass

    def query_positions(self):
        pass

    def receive_order(self):
        pass

    def run(self):
        self.t.RegisterFront(self.front_td)
        """
        
        registerFront==> onConnectFront ==> reqUserLogin
        ==> OnUserLogin ==>SubscribeMarketData(RB1901)
        ==> OnRtnDepthMarketData ==>q_OnTick
        ==> order ==> ReqOrderInsert ==> OnRspOrderInsert 报单已提交
        ==> OnRtnOrder 未成交==> ReqOrderAction(撤单)
        ==> OnRtnOrder 已撤单
        """

        self.t.SubscribePrivateTopic(nResumeType=2)  # quick
        self.t.SubscribePrivateTopic(nResumeType=2)
        self.t.Init()
        input()
        self.t.Release()


if __name__ == '__main__':
    z = QA_ATBroker(investor='008107', pwd='1')
    z.run()
