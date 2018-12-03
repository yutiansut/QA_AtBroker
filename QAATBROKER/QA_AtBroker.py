
import os
import platform
import sys
from time import sleep

import QACTP.ctp_struct as ctp
from QACTP.ctp_quote import Quote
from QACTP.ctp_trade import Trade

import _thread
import threading
import pandas as pd
import numpy as np
import QUANTAXIS as QA
import json
from QAPUBSUB import producer
from QUANTAXIS.QAMarket.QABroker import QA_Broker

sys.path.append(QA.QASetting.QALocalize.bin_path)  # 调用QA_Binpath下的dll


class QA_ATBroker(QA_Broker):
    def __init__(self, investor='008107', pwd='1', broker='9999', front_md='tcp://180.168.146.187:10031', front_td='tcp://180.168.146.187:10030'):

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
        self.market_data = []
        self.min_t = 0
        self._trading_code = []
        self.pro = producer.publisher(exchange='ctp')
        self.subscribed_code = []

    @property
    def trading_code(self):
        return set(self._trading_code)

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
        self.t.OnRspQryInvestorPosition = self.OnRspQryInvestorPosition
        self.t.OnRspQryTradingAccount = self.OnRspQryTradingAccount
        self.t.OnRspQryInvestor = self.OnRspQryInvestor

        self.t.OnRspQryTradingCode = self.OnRspQryTradingCode
        self.t.OnRspQryInstrumentMarginRate = self.OnRspQryInstrumentMarginRate
        self.t.OnRspQryInstrumentCommissionRate = self.OnRspQryInstrumentCommissionRate
        self.t.OnRspQryExchange = self.OnRspQryExchange
        self.t.OnRspQryProduct = self.OnRspQryProduct

        self.t.OnRspQryInstrument = self.OnRspQryInstrument
        self.t.OnRspQryDepthMarketData = self.OnRspQryDepthMarketData

        self.t.OnErrRtnOrderInsert = self.OnErrRtnOrderInsert
        self.t.OnErrRtnOrderAction = self.OnErrRtnOrderAction
        self.q.OnFrontConnected = self.q_OnFrontConnected
        self.q.OnRspUserLogin = self.q_OnRspUserLogin
        self.q.OnRtnDepthMarketData = self.q_OnTick

        self.t.RegCB()
        self.q.RegCB()

    def q_OnFrontConnected(self):
        QA.QA_util_log_info('connected')
        self.login()

    def q_OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        QA.QA_util_log_info('==============userlogin')
        QA.QA_util_log_info(info)
        # self.q.SubscribeMarketData('rb1901')
        self.subscribe(['rb1905'])

    def q_OnRtnDepthMarketData(self, pDepthMarketData: ctp.CThostFtdcDepthMarketDataField):
        QA.QA_util_log_info(
            'OnRtnDepthMarketData:, pDepthMarketData: CThostFtdcDepthMarketDataField')
        QA.QA_util_log_info(pDepthMarketData)

    def subscribe(self, code):
        if isinstance(code, list):
            for item in code:
                try:
                    self.q.SubscribeMarketData(item)
                    self.subscribed_code.append(item)
                except:
                    pass
        elif isinstance(code, str):
            self.subscribe([code])

    def OnFrontConnected(self):
        if not self.RelogEnable:
            return
        QA.QA_util_log_info('connected')
        if self.needAuth:
            self.t.ReqAuthenticate(
                # broker / investor / userProductionInfo / AuthCode
                self.broker, self.investor, '@yutiansut', '8MTL59FK1QGLKQW2')
        else:
            self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor,
                                Password=self.pwd, UserProductInfo='@yutiansut')

    def OnFrontDisconnected(self, reason: int):
        QA.QA_util_log_info(reason)

    def OnRspAuthenticate(self, pRspAuthenticateField: ctp.CThostFtdcRspAuthenticateField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info('auth：{0}:{1}'.format(
            pRspInfo.getErrorID(), pRspInfo.getErrorMsg()))
        self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor,
                            Password=self.pwd, UserProductInfo='@yutiansut')

    def OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        QA.QA_util_log_info(info.getErrorMsg())  # CTP:正确小于2种字符:请注意修改

        if info.getErrorID() == 0:
            self.Session = rsp.getSessionID()
            self.t.ReqSettlementInfoConfirm(
                BrokerID=self.broker, InvestorID=self.investor)
        else:
            self.RelogEnable = False

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm: ctp.CThostFtdcSettlementInfoConfirmField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        """确认成交信息
        """
        QA.QA_util_log_info('settlementInfo')
        QA.QA_util_log_info(pSettlementInfoConfirm)
        """
        example of  settlementInfoConfirm

        BrokerID = '9999', InvestorID = '106184', ConfirmDate = '20181116', ConfirmTime = '19:41:14', SettlementID = 0, AccountID = '', CurrencyID = ''
        """
        _thread.start_new_thread(self.StartQuote, ())

    def OnErrRtnOrderInsert(self, pInputOrder: ctp.CThostFtdcInputOrderField, pRspInfo: ctp.CThostFtdcRspInfoField):
        QA.QA_util_log_info(
            'OnErrRtnOrderInsert:, pInputOrder: CThostFtdcInputOrderField, pRspInfo: CThostFtdcRspInfoField')
        QA.QA_util_log_info(pInputOrder)
        QA.QA_util_log_info(pRspInfo)

    def OnErrRtnOrderAction(self, pOrderAction: ctp.CThostFtdcOrderActionField, pRspInfo: ctp.CThostFtdcRspInfoField):
        QA.QA_util_log_info(
            'OnErrRtnOrderAction:, pOrderAction: CThostFtdcOrderActionField, pRspInfo: CThostFtdcRspInfoField')
        QA.QA_util_log_info(pOrderAction)
        QA.QA_util_log_info(pRspInfo)

    def OnRtnInstrumentStatus(self, pInstrumentStatus: ctp.CThostFtdcInstrumentStatusField):
        # QA.QA_util_log_info('instrumentStatus')
        # QA.QA_util_log_info(str(pInstrumentStatus))
        """
        SHFE: 上期所返回的是rb
        其他交易所返回的是具体合约
        """

        self._trading_code.append(
            str(pInstrumentStatus.InstrumentID, encoding='utf-8'))

    def OnRspOrderInsert(self, pInputOrder: ctp.CThostFtdcInputOrderField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):

        QA.QA_util_log_info('ON_RSP_Order_INSERT')

        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(pInputOrder)
        QA.QA_util_log_info(pRspInfo.getErrorMsg())
        QA.QA_util_log_info(bIsLast)

    def OnRspQryInvestorPosition(self, pInvestorPosition: ctp.CThostFtdcInvestorPositionField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        """[summary]

        Arguments:
            pInvestorPosition {ctp.CThostFtdcInvestorPositionField} -- [description]
            pRspInfo {ctp.CThostFtdcRspInfoField} -- [description]
            nRequestID {int} -- [description]
            bIsLast {bool} -- [description]


        InstrumentID = 'cs1909',合约代码
        BrokerID = '9999', 经纪公司代码
        InvestorID = '106184', 投资者代码
        PosiDirection = PosiDirectionType.Short, 持仓多空方向
        HedgeFlag = HedgeFlagType.Speculation, 投机套保标志
        PositionDate = PositionDateType.Today, 持仓日期
        YdPosition = 1, 上日持仓
        Position = 1, 今日持仓
        LongFrozen = 0, 多头冻结
        ShortFrozen = 0, 空头冻结
        LongFrozenAmount = 0.0,开多仓冻结金额
        ShortFrozenAmount = 0.0, 开空仓冻结金额 
        OpenVolume = 0, 开仓量
        CloseVolume = 0, 平仓量
        OpenAmount = 0.0,  开仓金额
        CloseAmount = 0.0, 平仓金额
        PositionCost = 24870.0, 持仓成本
        PreMargin = 0.0,上次占用的保证金
        UseMargin = 1243.5, 占用的保证金
        FrozenMargin = 0.0,冻结的保证金
        FrozenCash = 0.0, 冻结的资金
        FrozenCommission = 0.0,冻结的手续费
        CashIn = 0.0, 资金差额
        Commission = 0.0,手续费
        CloseProfit = 0.0, 平仓盈亏
        PositionProfit = 30.0,持仓盈亏
        PreSettlementPrice = 2487.0, 上次结算价
        SettlementPrice = 2484.0,本次结算价
        TradingDay = '20181116', 交易日
        SettlementID = 1,结算编号
        OpenCost = 25080.0, 开仓成本
        ExchangeMargin = 1243.5,  交易所保证金
        CombPosition = 0,组合成交形成的持仓
        CombLongFrozen = 0,组合多头冻结
        CombShortFrozen = 0, 组合空头冻结
        CloseProfitByDate = 0.0,逐日盯市平仓盈亏
        CloseProfitByTrade = 0.0, 逐笔对冲平仓盈亏
        TodayPosition = 0,  今日持仓
        MarginRateByMoney = 0.0, 保证金率
        MarginRateByVolume = 0.0,  保证金率(按手数)
        StrikeFrozen = 0,  执行冻结
        StrikeFrozenAmount = 0.0, 执行冻结金额
        AbandonFrozen = 0, 放弃执行冻结
        ExchangeID = '',  交易所代码
        YdStrikeFrozen = 0, 执行冻结的昨仓
        InvestUnitID = ''投资单元代码

        """
        QA.QA_util_log_info(
            'OnRspQryInvestorPosition:, pInvestorPosition: CThostFtdcInvestorPositionField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pInvestorPosition)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryTradingAccount(self, pTradingAccount: ctp.CThostFtdcTradingAccountField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        """[summary]

        Arguments:
            pTradingAccount {ctp.CThostFtdcTradingAccountField} -- [description]
            pRspInfo {ctp.CThostFtdcRspInfoField} -- [description]
            nRequestID {int} -- [description]
            bIsLast {bool} -- [description]


        BrokerID = '9999', 经纪公司代码
        AccountID = '106184',投资者帐号 
        PreMortgage = 0.0, 上次质押金额
        PreCredit = 0.0, 上次信用额度
        PreDeposit = 1442538.31, 上次存款额
        PreBalance = 1443781.81, 上次结算准备金
        PreMargin = 1243.5, 上次占用的保证金
        InterestBase = 0.0, 利息基数
        Interest = 0.0, 利息收入
        Deposit = 0.0, 入金金额 
        Withdraw = 0.0, 出金金额
        FrozenMargin = 96536.0, 冻结的保证金
        FrozenCash = 0.0, 冻结的资金
        FrozenCommission = 107.4538, 冻结的手续费
        CurrMargin = 1243.5, 当前保证金总额
        CashIn = 0.0, 资金差额
        Commission = 0.0, 手续费
        CloseProfit = 0.0,平仓盈亏
        PositionProfit = 30.0, 持仓盈亏
        Balance = 1443811.81, 期货结算准备金
        Available = 1345894.8562,可用资金
        WithdrawQuota = 1076715.8849600002,可取资金
        Reserve = 0.0,基本准备金
        TradingDay = '20181116', 交易日
        SettlementID = 1,结算编号
        Credit = 0.0, 信用额度
        Mortgage = 0.0, 质押金额
        ExchangeMargin = 1243.5, 交易所保证金
        DeliveryMargin = 0.0, 投资者交割保证金
        ExchangeDeliveryMargin = 0.0,交易所交割保证金
        ReserveBalance = 0.0, 保底期货结算准备金
        CurrencyID = 'CNY', 币种代码
        PreFundMortgageIn = 0.0, 上次货币质入金额
        PreFundMortgageOut = 0.0, 上次货币质出金额
        FundMortgageIn = 0.0,货币质入金额
        FundMortgageOut = 0.0, 货币质出金额
        FundMortgageAvailable = 0.0, 货币质押余额
        MortgageableFund = 1076715.8849600002,可质押货币金额
        SpecProductMargin = 0.0, 特殊产品占用保证金
        SpecProductFrozenMargin = 0.0, 特殊产品冻结保证金
        SpecProductCommission = 0.0, 特殊产品手续费
        SpecProductFrozenCommission = 0.0,特殊产品冻结手续费
        SpecProductPositionProfit = 0.0, 特殊产品持仓盈亏
        SpecProductCloseProfit = 0.0, 特殊产品平仓盈亏
        SpecProductPositionProfitByAlg = 0.0, 根据持仓盈亏算法计算的特殊产品持仓盈亏
        SpecProductExchangeMargin = 0.0, 特殊产品交易所保证金
        BizType = BizTypeType., 业务类型
        FrozenSwap = 0.0,延时换汇冻结金额
        RemainSwap = 0.0剩余换汇额度
        """

        QA.QA_util_log_info(
            'OnRspQryTradingAccount:, pTradingAccount: CThostFtdcTradingAccountField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pTradingAccount)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryInvestor(self, pInvestor: ctp.CThostFtdcInvestorField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        """[summary]

        Arguments:
            pInvestor {ctp.CThostFtdcInvestorField} -- [description]
            pRspInfo {ctp.CThostFtdcRspInfoField} -- [description]
            nRequestID {int} -- [description]
            bIsLast {bool} -- [description]

                ("InvestorID", c_char*13),
        # 经纪公司代码
        ("BrokerID", c_char*11),
        # 投资者分组代码
        ("InvestorGroupID", c_char*13),
        # 投资者名称
        ("InvestorName", c_char*81),
        # 证件类型
        ("IdentifiedCardType", c_char),
        # 证件号码
        ("IdentifiedCardNo", c_char*51),
        # 是否活跃
        ("IsActive", c_int32),
        # 联系电话
        ("Telephone", c_char*41),
        # 通讯地址
        ("Address", c_char*101),
        # 开户日期
        ("OpenDate", c_char*9),
        # 手机
        ("Mobile", c_char*41),
        # 手续费率模板代码
        ("CommModelID", c_char*13),
        # 保证金率模板代码
        ("MarginModelID", c_char*13),
        """

        QA.QA_util_log_info(
            'OnRspQryInvestor:, pInvestor: CThostFtdcInvestorField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pInvestor)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryTradingCode(self, pTradingCode: ctp.CThostFtdcTradingCodeField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info(
            'OnRspQryTradingCode:, pTradingCode: CThostFtdcTradingCodeField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pTradingCode)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryInstrumentMarginRate(self, pInstrumentMarginRate: ctp.CThostFtdcInstrumentMarginRateField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info(
            'OnRspQryInstrumentMarginRate:, pInstrumentMarginRate: CThostFtdcInstrumentMarginRateField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pInstrumentMarginRate)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryInstrumentCommissionRate(self, pInstrumentCommissionRate: ctp.CThostFtdcInstrumentCommissionRateField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info(
            'OnRspQryInstrumentCommissionRate:, pInstrumentCommissionRate: CThostFtdcInstrumentCommissionRateField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pInstrumentCommissionRate)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryExchange(self, pExchange: ctp.CThostFtdcExchangeField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info(
            'OnRspQryExchange:, pExchange: CThostFtdcExchangeField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pExchange)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryProduct(self, pProduct: ctp.CThostFtdcProductField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info(
            'OnRspQryProduct:, pProduct: CThostFtdcProductField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pProduct)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryInstrument(self, pInstrument: ctp.CThostFtdcInstrumentField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info(
            'OnRspQryInstrument:, pInstrument: CThostFtdcInstrumentField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(str(pInstrument))
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRspQryDepthMarketData(self, pDepthMarketData: ctp.CThostFtdcDepthMarketDataField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        QA.QA_util_log_info('DEPTH MARKET')
        QA.QA_util_log_info(
            'OnRspQryDepthMarketData:, pDepthMarketData: CThostFtdcDepthMarketDataField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        QA.QA_util_log_info(pDepthMarketData)
        QA.QA_util_log_info(pRspInfo)
        QA.QA_util_log_info(nRequestID)
        QA.QA_util_log_info(bIsLast)

    def OnRtnOrder(self, pOrder: ctp.CThostFtdcOrderField):
        QA.QA_util_log_info('===ON_RTN_ORDE===')
        QA.QA_util_log_info(pOrder)
        QA.QA_util_log_info(pOrder.getOrderStatus())
        QA.QA_util_log_info('===END_RTN_ORDE===')
        # if pOrder.getSessionID() == self.Session and pOrder.getOrderStatus() == ctp.OrderStatusType.NoTradeQueueing:
        #     QA.QA_util_log_info("撤单")
        #     self.t.ReqOrderAction(
        #         self.broker, self.investor,
        #         InstrumentID=pOrder.getInstrumentID(),
        #         OrderRef=pOrder.getOrderRef(),
        #         FrontID=pOrder.getFrontID(),
        #         SessionID=pOrder.getSessionID(),
        #         ActionFlag=ctp.ActionFlagType.Delete)

    def tick_handle(self, tick: ctp.CThostFtdcMarketDataField):
        z = vars(tick)
        if isinstance(z, dict):
            z = json.dumps(z)
            #print(z)

            self.pro.pub(z)
        else:
            print(z)
        # self.market_data.append(pd.DataFrame([vars(tick)]))
        # df = pd.concat(self.market_data)
        # df = df.assign(datetime=df.ActionDay.apply(str)+' ' +
        #                df.UpdateTime.apply(str) + ' ' + df.UpdateMillisec.apply(str), code=df.InstrumentID).set_index(['datetime', 'code'])
        # df = df.replace(1.7976931348623157e+308, np.nan).dropna(axis='columns')

        # self.min_t += 1

        # if self.min_t % 10 == 0:
        #     QA.QA_util_log_info(df)
        #     QA.QA_util_log_info(threading.enumerate())

    def q_OnTick(self, tick: ctp.CThostFtdcMarketDataField):
        self.tick_handle(tick)
        #f = tick
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
        # QA.QA_util_log_info(self.trading_code)
        #_thread.start_new_thread(self.tick_handle, (tick,))
        # if not self.ordered:
        #     _thread.start_new_thread(self.Order, (f,))
        #     self.ordered = True

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
        # while True:
        #     sleep(1.1)
        #     self.t.ReqQryTradingAccount(self.broker, self.investor)
        #     sleep(1.1)
        #     #self.t.ReqQryInvestorPosition(self.broker, self.investor)
        #     return

    def Order(self, f: ctp.CThostFtdcMarketDataField):
        QA.QA_util_log_info("报单")
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
            LimitPrice=f.getLastPrice() + 50,
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

        ReqQryTradingAccount(self.broker, self.investor)
        ReqQryInvestorPosition(self.broker, self.investor)

        
        ==> OnUserLogin ==>SubscribeMarketData(RB1901)
        ==> OnRtnDepthMarketData ==>q_OnTick
        ==> order ==> ReqOrderInsert ==> OnRspOrderInsert 报单已提交
        ==> OnRtnOrder 未成交==> ReqOrderAction(撤单)
        ==> OnRtnOrder 已撤单
        """

        self.t.SubscribePrivateTopic(nResumeType=2)  # quick
        # self.t.SubscribePrivateTopic(nResumeType=2)
        self.t.Init()

        self.t.ReqQryDepthMarketData('rb1905', 'SHFE')
        self.t.ReqQryTradingAccount(self.broker, self.investor)
        self.Qry()
        # print(self.t.orders)
        #self.t.ReqQryInvestor(self.broker, self.investor)
        sleep(1.1)
        self.t.ReqQryInvestorPosition(self.broker, self.investor)

        input()
        self.t.Release()


if __name__ == '__main__':
    z = QA_ATBroker(front_md='tcp://218.202.237.33:10012',front_td='tcp://218.202.237.33:10002')
    z.run()
