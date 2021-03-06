from operator import methodcaller
import time
import threading
import redis
import json
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
from redistimeseries.client import Client
import alpaca_trade_api as alpaca


class StudyScores:
    KeyName = ""
    Symbol = ""
    Score = 0
    Fluctuation = 0
    KeyLevel = 0
    MultiTimeFrame = 0
    CandleStickPattern = 0
    PriceAction = 0
    FibonacciPattern = 0
    RsiAction = 0
    Ema50 = 0
    Vwap = 0
    News = 0
    Correlation = 0
    WithTrend = 0
    BreakoutMomentum = 0
    FreshTrend = 0
    Level2 = 0
    Total = 0

    def __init__(self, key, symbol):
        self.KeyName = key
        self.Symbol = symbol

    # serialize class
    def serialize(self):
        return {
            'KeyName': self.KeyName,
            'Symbol': self.Symbol,
            'Score': self.Score,
            'Fluctuation': self.Fluctuation,
            'KeyLevel': self.KeyLevel,
            'MultiTimeFrame': self.MultiTimeFrame,
            'CandleStickPattern': self.CandleStickPattern,
            'PriceAction': self.PriceAction,
            'FibonacciPattern': self.FibonacciPattern,
            'RsiAction': self.RsiAction,
            'Ema50': self.Ema50,
            'Vwap': self.Vwap,
            'News': self.News,
            'Correlation': self.Correlation,
            'WithTrend': self.WithTrend,
            'BreakoutMomentum': self.BreakoutMomentum,
            'FreshTrend': self.FreshTrend,
            'Level2': self.Level2,
            'Total': self.Total
        }

    def serialize_to_string(self):
        return json.dumps(self.serialize())

    def deserialize(self, data=None):
        if data is None:
            data = self.serialize()
        self.KeyName = data['KeyName']
        self.Symbol = data['Symbol']
        self.Score = data['Score']
        self.Fluctuation = data['Fluctuation']
        self.KeyLevel = data['KeyLevel']
        self.MultiTimeFrame = data['MultiTimeFrame']
        self.CandleStickPattern = data['CandleStickPattern']
        self.PriceAction = data['PriceAction']
        self.FibonacciPattern = data['FibonacciPattern']
        self.RsiAction = data['RsiAction']
        self.Ema50 = data['Ema50']
        self.Vwap = data['Vwap']
        self.News = data['News']
        self.Correlation = data['Correlation']
        self.WithTrend = data['WithTrend']
        self.BreakoutMomentum = data['BreakoutMomentum']
        self.FreshTrend = data['FreshTrend']
        self.Level2 = data['Level2']
        self.Total = data['Total']

    def deserialize_from_string(self, data=None):
        if data is None:
            data = self.serialize()
        self.deserialize(json.loads(data))

    def __str__(self):
        str = self.serialize_to_string()
        return str


class RedisTimeFrame:
    REALTIME = "0"
    MIN1 = "1MIN"
    MIN2 = "2MIN"
    MIN5 = "5MIN"
    MIN30 = "30MIN"
    HOUR = "HOUR"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class RetentionTime:
    SECOND = 1000
    MINUTE = 60000
    HOUR = 360000


class RealTimeStockData:
    IEX = 'IEX'
    ALPACA = 'ALPACA'


def bar_key(symbol, suffix, timeframe):
    return "data_" + suffix + "_" + timeframe + ":" + symbol


class AlpacaAccess:
    ALPACA_API_KEY = 'AKAV2Z5H0NJNXYF7K24D'
    ALPACA_SECRET_KEY = '262cAEeIRrL1KEZYKSTjZA79tj25XWrMtvz0Bezu'
    ALPACA_API_URL = 'https://api.alpaca.markets'
    ALPACA_WS = 'wss://stream.data.alpaca.markets/v2'
    ALPACA_FEED = 'sip'  # <- replace to SIP if you have PRO subscription

    @staticmethod
    def connection():
        api = alpaca.REST(
            AlpacaAccess.ALPACA_API_KEY, AlpacaAccess.ALPACA_SECRET_KEY, AlpacaAccess.ALPACA_API_URL)
        return api


class AlpacaStreamAccess:
    @staticmethod
    def connection():
        return Stream(AlpacaAccess.ALPACA_API_KEY,
                      AlpacaAccess.ALPACA_SECRET_KEY,
                      base_url=URL(AlpacaAccess.ALPACA_WS),
                      data_feed=AlpacaAccess.ALPACA_FEED,
                      raw_data=True)


class RedisAccess:

    @staticmethod
    def connection(r=None):
        if (r == None):
            return redis.StrictRedis(
                host='127.0.0.1', port=6379, db=0)
        else:
            return r


class TimeSeriesAccess:
    @staticmethod
    def connection(r=None):
        if (r == None):
            return Client(host='127.0.0.1', port=6379)
        else:
            return r

    @staticmethod
    def connect(r=None):
        if (r == None):
            rds = redis.StrictRedis(
                host='127.0.0.1', port=6379, db=0)
            return redis.TimeSeries(rds, base_key='my_timeseries')
        else:
            return r

    @staticmethod
    def RealTimeSymbols():
        redis = RedisAccess.connection()
        symbols = []
        realTimeSymbols = redis.keys("data_close_0:*")
        for realTimeSymbol in realTimeSymbols:
            symbol = bytes.decode(realTimeSymbol).split(":")[1]
            symbols.append(symbol)
        return symbols


class KeyName:
    # step 1: new bar data is sent.  It is appened to the redis pub/sub
    EVENT_BAR2DB = ["RPS_BAR_RTS"]
    # step 2: once it is added to the redis timeseries, it is sent to new bar storage
    EVENT_BAR2CACHE = ["RPS_BAR_CACHE"]
    # step 3: once the data passes the filter, it is sent to the new bar stack
    EVENT_BAR2STACK = ["RPS_ANALYSIS_STACK"]
    # step 4: data is scored, and the result is stored in sorted set, dashboard and score
    EVENT_BAR2STACK_NEW = ["RPS_ANALYSIS_STACK_NEW"]
    EVENT_BAR2SCORE = ["RPS_SAVE_SCORE"]
    EVENT_NEW_CANDIDATES = ["RPS_THREEBARSTACK_NEW"]

    KEY_THREEBARSTACK = "STUDYTHREEBARSTACK"
    KEY_THREEBARSTACK_SUBSCRIBE = "STUDYTHREEBARSTACK_SUBSCRIBE"
    KEY_THREEBARSTACK_UNSUBSCRIBE = "STUDYTHREEBARSTACK_UNSUBSCRIBE"
    KEY_THREEBARSCORE = "STUDYTHREEBARSCORE"

    STUDY_KEY_LEVELS = "STUDY_KEY_LEVELS"

    # UPDATED BARS
    VARIABLE_ACTIVE_BARS = "ACTIVE_BARS"    # active bar

    # Time Series Key for each symbol, data type and timeframe

    @staticmethod
    def KeyBar(symbol, datatype, timeframe):
        return "RTS_BAR_" + datatype.upper() + "_" + timeframe + ":" + symbol.upper()

    # Sorted Set key for Dashboard for quick lookup
    @staticmethod
    def KeyDashboard():
        return "RSS_DAASHBOARD"

    # Hashed key for scores.  Historical data.  24 hours.
    @staticmethod
    def KeyScore(symbol):
        return "RTS_SCORE:" + symbol.upper()


#
# {'close': 136.02,
#  'high': 136.06,
#  'low': 136.0,
#  'open': 136.04,
#  'symbol': 'ALLE',
#  'timestamp': 1627493640000000000,
#  'trade_count': 22,
#  'volume': 712,
#  'vwap': 136.030153}
#


class TimeStamp:

    @staticmethod
    def get_starttime(timeframe):
        second = RetentionTime.SECOND
        minute = 60 * second
        hour = 60 * minute
        now_ms = TimeStamp.now()
        switcher = {
            RedisTimeFrame.REALTIME: now_ms - (second * 30),
            RedisTimeFrame.MIN1: now_ms - (minute * 5),
            RedisTimeFrame.MIN2: now_ms - (minute * 10),
            RedisTimeFrame.MIN5: now_ms - (hour),
            RedisTimeFrame.MIN30: now_ms - (hour * 4),
        }
        dt = switcher.get(timeframe)
        return dt

    @staticmethod
    def get_endtime(timeframe):
        return TimeStamp.now()

    @staticmethod
    def retention_in_ms(timeframe):
        second = 1000
        minute = 60000
        hour = 360000
        switcher = {
            RedisTimeFrame.REALTIME: 5 * minute,
            RedisTimeFrame.MIN1: 15 * minute,
            RedisTimeFrame.MIN2: 30 * minute,
            RedisTimeFrame.MIN5: 4 * hour
        }
        dt = switcher.get(timeframe)
        return dt

    @staticmethod
    def now():
        return int(time.time() * 1000)
        # return int(time.time_ns() / 1000)


class SetInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = threading.Event()
        thread = threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time.time()+self.interval
        while not self.stopEvent.wait(nextTime-time.time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()


class MarketData:
    def __init__(self, api, redisCore: redis):
        self.api = api
        self.redisCore = redisCore

    def _getTicks(timeframe):
        return 365

    def _download(self, symbol, timeframe):
        barset = self.api.get_barset(
            symbol, 'day', limit=self._getTicks(timeframe))
        stock_bars = barset[symbol]
        return stock_bars

    def _key(self, symbol, oneDate):
        return "D" + oneDate.strftime("%y%m%d") + ":" + symbol

    def data(self, symbol, timeframe):
        pass


if __name__ == "__main__":
    print(RedisTimeFrame.REALTIME)
