#
from queue import Queue
from collections import deque


class tickhandler():
    def __init__(self):
        self.market_data = {}

    def init_md(self, varities):
        pass

    def upcomingdata(self, upcomingdata):
        try:
            code = upcomingdata.get(
                'code', upcomingdata.get('InstrumentID', None))
            self.market_data[code] = upcomingdata

            
        except:
            pass
