# coding:utf-8

import QUANTAXIS as QA

from py_ctp import test_trade, test_api

import time
tt = test_trade.TestTrade()
# t.OnConnected = t.ReqUserLogin('008105', '1', '9999')
# t.ReqConnect('tcp://180.168.146.187:10000')
tt.run()

time.sleep(6)
for inst in tt.t.instruments.values():
    print(inst)
print(tt.t.orders)
print(tt.t.trades)
z = test_api.Test()

z.Run()
input()
z.t.Release()
input()

# ReqOrderAction(
#                 self.broker, self.investor,
#                 InstrumentID=pOrder.getInstrumentID(),
#                 OrderRef=pOrder.getOrderRef(),
#                 FrontID=pOrder.getFrontID(),
#                 SessionID=pOrder.getSessionID(),
#                 ActionFlag=ctp.ActionFlagType.Delete)

# ReqOrderInsert(
#             BrokerID=self.broker,
#             InvestorID=self.investor,
#             InstrumentID=f.getInstrumentID(),
#             OrderRef='{0:>12}'.format(self.req),
#             UserID=self.investor,
#             OrderPriceType=ctp.OrderPriceTypeType.LimitPrice,
#             Direction=ctp.DirectionType.Buy,
#             CombOffsetFlag=ctp.OffsetFlagType.Open.__char__(),
#             CombHedgeFlag=ctp.HedgeFlagType.Speculation.__char__(),
#             LimitPrice=f.getLastPrice() - 50,
#             VolumeTotalOriginal=1,
#             TimeCondition=ctp.TimeConditionType.GFD,
#             # GTDDate=''
#             VolumeCondition=ctp.VolumeConditionType.AV,
#             MinVolume=1,
#             ContingentCondition=ctp.ContingentConditionType.Immediately,
#             StopPrice=0,
#             ForceCloseReason=ctp.ForceCloseReasonType.NotForceClose,
#             IsAutoSuspend=0,
#             IsSwapOrder=0,
#             UserForceClose=0)


# tt.t.ReqOrderInsert()
# tt.t.ReqOrderAction()
# tt.release()
