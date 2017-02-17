from datetime import datetime
import inspect
import requests
import sys
from threading import Thread
import time
import traceback
import csv
from decimal import Decimal

from electrum_stratis.stratis import COIN
from electrum_stratis.plugins import BasePlugin, hook
from electrum_stratis.i18n import _
from electrum_stratis.util import PrintError, ThreadJob
from electrum_stratis.util import format_satoshis


# See https://en.wikipedia.org/wiki/ISO_4217
CCY_PRECISIONS = {'BHD': 3, 'BIF': 0, 'BYR': 0, 'CLF': 4, 'CLP': 0,
                  'CVE': 0, 'DJF': 0, 'GNF': 0, 'IQD': 3, 'ISK': 0,
                  'JOD': 3, 'JPY': 0, 'KMF': 0, 'KRW': 0, 'KWD': 3,
                  'LYD': 3, 'MGA': 1, 'MRO': 1, 'OMR': 3, 'PYG': 0,
                  'RWF': 0, 'TND': 3, 'UGX': 0, 'UYI': 0, 'VND': 0,
                  'VUV': 0, 'XAF': 0, 'XAU': 4, 'XOF': 0, 'XPF': 0}

class ExchangeBase(PrintError):

    def __init__(self, on_quotes, on_history):
        self.history = {}
        self.quotes = {}
        self.on_quotes = on_quotes
        self.on_history = on_history

    def get_json(self, site, get_string):
        # APIs must have https
        url = ''.join(['https://', site, get_string])
        response = requests.request('GET', url, headers={'User-Agent' : 'Electrum'})
        return response.json()

    def get_csv(self, site, get_string):
        url = ''.join(['https://', site, get_string])
        response = requests.request('GET', url, headers={'User-Agent' : 'Electrum'})
        reader = csv.DictReader(response.content.split('\n'))
        return list(reader)

    def name(self):
        return self.__class__.__name__

    def update_safe(self, ccy):
        try:
            self.print_error("getting fx quotes for", ccy)
            self.quotes = self.get_rates(ccy)
            self.print_error("received fx quotes")
        except BaseException as e:
            self.print_error("failed fx quotes:", e)
        self.on_quotes()

    def update(self, ccy):
        t = Thread(target=self.update_safe, args=(ccy,))
        t.setDaemon(True)
        t.start()

    def get_historical_rates_safe(self, ccy):
        try:
            self.print_error("requesting fx history for", ccy)
            self.history[ccy] = self.historical_rates(ccy)
            self.print_error("received fx history for", ccy)
            self.on_history()
        except BaseException as e:
            self.print_error("failed fx history:", e)

    def get_historical_rates(self, ccy):
        result = self.history.get(ccy)
        if not result and ccy in self.history_ccys():
            t = Thread(target=self.get_historical_rates_safe, args=(ccy,))
            t.setDaemon(True)
            t.start()
        return result

    def history_ccys(self):
        return []

    def historical_rate(self, ccy, d_t):
        return self.history.get(ccy, {}).get(d_t.strftime('%Y-%m-%d'))

    def get_currencies(self):
        rates = self.get_rates('')
        return [str(a) for (a, b) in rates.iteritems() if b is not None]


class Bit2C(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('api.bitcoinaverage.com', '/ticker/global/all')
        return dict([(r, Decimal(json[r]['last']))
                     for r in json if r != 'timestamp'])

    def history_ccys(self):
        return ['AUD', 'BRL', 'CAD', 'CHF', 'CNY', 'EUR', 'GBP', 'IDR', 'ILS',
                'MXN', 'NOK', 'NZD', 'PLN', 'RON', 'RUB', 'SEK', 'SGD', 'USD',
                'ZAR']

    def historical_rates(self, ccy):
        history = self.get_csv('api.bitcoinaverage.com',
                               "/history/%s/per_day_all_time_history.csv" % ccy)
        return dict([(h['DateTime'][:10], h['Average'])
                     for h in history])

class BitcoinVenezuela(ExchangeBase):

    def get_rates(self, ccy):
        json = self.get_json('api.bitcoinvenezuela.com', '/')
        rates = [(r, json['STRAT'][r]) for r in json['STRAT']
                 if json['STRAT'][r] is not None]  # Giving NULL sometimes
        return dict(rates)

    def history_ccys(self):
        return ['ARS', 'EUR', 'USD', 'VEF']

    def historical_rates(self, ccy):
        json = self.get_json('api.bitcoinvenezuela.com',
                             '/historical/index.php?coin=STRAT')
        return json[ccy +'_STRAT']

class BTCParalelo(ExchangeBase):

    def get_rates(self, ccy):
        json = self.get_json('btcparalelo.com', '/api/price')
        return {'VEF': Decimal(json['price'])}


class Bitso(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('api.bitso.com', '/v2/ticker')
        return {'MXN': Decimal(json['last'])}


class Bitmarket(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.bitmarket.pl', '/json/BTCPLN/ticker.json')
        return {'PLN': Decimal(json['last'])}

class BitPay(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('bitpay.com', '/api/rates')
        return dict([(r['code'], Decimal(r['rate'])) for r in json])

class BitStamp(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.bitstamp.net', '/api/ticker/')
        return {'USD': Decimal(json['last'])}

class BlockchainInfo(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('blockchain.info', '/ticker')
        return dict([(r, Decimal(json[r]['15m'])) for r in json])

class BTCChina(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('data.btcchina.com', '/data/ticker?market=stratcny')
        return {'CNY': Decimal(json['ticker']['last'])}

class BTCe(ExchangeBase):
    def get_rates(self, ccy):
        ccys = ['EUR', 'RUR', 'USD']
        ccy_str = '-'.join(['strat_%s' % c.lower() for c in ccys])
        json = self.get_json('btc-e.com', '/api/3/ticker/%s' % ccy_str)
        result = dict.fromkeys(ccys)
        for ccy in ccys:
            result[ccy] = Decimal(json['strat_%s' % ccy.lower()]['last'])
        return result

class CaVirtEx(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.cavirtex.com', '/api2/ticker.json?currencypair=STRATCAD')
        return {'CAD': Decimal(json['ticker']['STRATCAD']['last'])}

class CoinSpot(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.coinspot.com.au', '/pubapi/latest')
        return {'AUD': Decimal(json['prices']['strat']['last'])}

class GoCoin(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('x.g0cn.com', '/prices')
        strat_prices = json['prices']['STRAT']
        return dict([(r, Decimal(strat_prices[r])) for r in strat_prices])

class HitBTC(ExchangeBase):
    def get_rates(self, ccy):
        ccys = ['EUR', 'USD']
        json = self.get_json('api.hitbtc.com', '/api/1/public/STRAT%s/ticker' % ccy)
        result = dict.fromkeys(ccys)
        if ccy in ccys:
            result[ccy] = Decimal(json['last'])
        return result

class Kraken(ExchangeBase):
    def get_rates(self, ccy):
        dicts = self.get_json('api.kraken.com', '/0/public/AssetPairs')
        pairs = [k for k in dicts['result'] if k.startswith('XSTRATZ')]
        json = self.get_json('api.kraken.com',
                             '/0/public/Ticker?pair=%s' % ','.join(pairs))
        ccys = [p[5:] for p in pairs]
        result = dict.fromkeys(ccys)
        result[ccy] = Decimal(json['result']['XSTRATZ'+ccy]['c'][0])
        return result

    def history_ccys(self):
        return ['EUR', 'USD']

    def historical_rates(self, ccy):
        query = '/0/public/OHLC?pair=STRAT%s&interval=1440' % ccy
        json = self.get_json('api.kraken.com', query)
        history = json['result']['XSTRATZ'+ccy]
        return dict([(time.strftime('%Y-%m-%d', time.localtime(t[0])), t[4])
                                    for t in history])

class OKCoin(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.okcoin.cn', '/api/ticker.do?symbol=strat_cny')
        return {'CNY': Decimal(json['ticker']['last'])}

class MercadoBitcoin(ExchangeBase):
    def get_rates(self, ccy):
	json = self.get_json('api.bitvalor.com', '/v1/ticker.json')
        return {'BRL': Decimal(json['ticker_1h']['exchanges']['MBT']['last'])}

class Bitcointoyou(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('bitcointoyou.com', "/API/ticker.aspx")
        return {'BRL': Decimal(json['ticker']['last'])}

    def history_ccys(self):
        return ['BRL']

class Bitvalor(ExchangeBase):
    def get_rates(self,ccy):
	json = self.get_json('api.bitvalor.com', '/v1/ticker.json')
        return {'BRL': Decimal(json['ticker_1h']['total']['last'])}


class Foxbit(ExchangeBase):
    def get_rates(self,ccy):
	json = self.get_json('api.bitvalor.com', '/v1/ticker.json')
        return {'BRL': Decimal(json['ticker_1h']['exchanges']['FOX']['last'])}

class NegocieCoins(ExchangeBase):
    def get_rates(self,ccy):
	json = self.get_json('api.bitvalor.com', '/v1/ticker.json')
        return {'BRL': Decimal(json['ticker_1h']['exchanges']['NEG']['last'])}

    def history_ccys(self):
        return ['BRL']


def dictinvert(d):
    inv = {}
    for k, vlist in d.iteritems():
        for v in vlist:
            keys = inv.setdefault(v, [])
            keys.append(k)
    return inv

def get_exchanges_and_currencies():
    import os, json
    path = os.path.join(os.path.dirname(__file__), 'currencies.json')
    try:
        return json.loads(open(path, 'r').read())
    except:
        pass
    d = {}
    is_exchange = lambda obj: (inspect.isclass(obj)
                               and issubclass(obj, ExchangeBase)
                               and obj != ExchangeBase)
    exchanges = dict(inspect.getmembers(sys.modules[__name__], is_exchange))
    for name, klass in exchanges.items():
        exchange = klass(None, None)
        try:
            d[name] = exchange.get_currencies()
        except:
            continue
    with open(path, 'w') as f:
        f.write(json.dumps(d, indent=4, sort_keys=True))
    return d


CURRENCIES = get_exchanges_and_currencies()


def get_exchanges_by_ccy(history=True):
    if not history:
        return dictinvert(CURRENCIES)
    d = {}
    exchanges = CURRENCIES.keys()
    for name in exchanges:
        klass = globals()[name]
        exchange = klass(None, None)
        d[name] = exchange.history_ccys()
    return dictinvert(d)



class FxThread(ThreadJob):

    def __init__(self, config, network):
        self.config = config
        self.network = network
        self.ccy = self.get_currency()
        self.history_used_spot = False
        self.ccy_combo = None
        self.hist_checkbox = None
        self.set_exchange(self.config_exchange())

    def get_currencies(self, h):
        d = get_exchanges_by_ccy(h)
        return sorted(d.keys())

    def get_exchanges_by_ccy(self, ccy, h):
        d = get_exchanges_by_ccy(h)
        return d.get(ccy, [])

    def ccy_amount_str(self, amount, commas):
        prec = CCY_PRECISIONS.get(self.ccy, 2)
        fmt_str = "{:%s.%df}" % ("," if commas else "", max(0, prec))
        return fmt_str.format(round(amount, prec))

    def run(self):
        # This runs from the plugins thread which catches exceptions
        if self.is_enabled():
            if self.timeout ==0 and self.show_history():
                self.exchange.get_historical_rates(self.ccy)
            if self.timeout <= time.time():
                self.timeout = time.time() + 150
                self.exchange.update(self.ccy)

    def is_enabled(self):
        return bool(self.config.get('use_exchange_rate'))

    def set_enabled(self, b):
        return self.config.set_key('use_exchange_rate', bool(b))

    def get_history_config(self):
        return bool(self.config.get('history_rates'))

    def set_history_config(self, b):
        self.config.set_key('history_rates', bool(b))

    def get_currency(self):
        '''Use when dynamic fetching is needed'''
        return self.config.get("currency", "EUR")

    def config_exchange(self):
        return self.config.get('use_exchange', 'BTCe')

    def show_history(self):
        return self.is_enabled() and self.get_history_config() and self.ccy in self.exchange.history_ccys()

    def set_currency(self, ccy):
        self.ccy = ccy
        self.config.set_key('currency', ccy, True)
        self.timeout = 0 # Because self.ccy changes
        self.on_quotes()

    def set_exchange(self, name):
        class_ = globals().get(name, BitcoinAverage)
        self.print_error("using exchange", name)
        if self.config_exchange() != name:
            self.config.set_key('use_exchange', name, True)
        self.exchange = class_(self.on_quotes, self.on_history)
        # A new exchange means new fx quotes, initially empty.  Force
        # a quote refresh
        self.timeout = 0

    def on_quotes(self):
        self.network.trigger_callback('on_quotes')

    def on_history(self):
        self.network.trigger_callback('on_history')

    def exchange_rate(self):
        '''Returns None, or the exchange rate as a Decimal'''
        rate = self.exchange.quotes.get(self.ccy)
        if rate:
            return Decimal(rate)

    def format_amount_and_units(self, btc_balance):
        rate = self.exchange_rate()
        return '' if rate is None else "%s %s" % (self.value_str(btc_balance, rate), self.ccy)

    def get_fiat_status_text(self, btc_balance):
        rate = self.exchange_rate()
        return _("  (No FX rate available)") if rate is None else " 1 BTC~%s %s" % (self.value_str(COIN, rate), self.ccy)


    def value_str(self, satoshis, rate):
        if satoshis is None:  # Can happen with incomplete history
            return _("Unknown")
        if rate:
            value = Decimal(satoshis) / COIN * Decimal(rate)
            return "%s" % (self.ccy_amount_str(value, True))
        return _("No data")

    def history_rate(self, d_t):
        rate = self.exchange.historical_rate(self.ccy, d_t)
        # Frequently there is no rate for today, until tomorrow :)
        # Use spot quotes in that case
        if rate is None and (datetime.today().date() - d_t.date()).days <= 2:
            rate = self.exchange.quotes.get(self.ccy)
            self.history_used_spot = True
        return rate

    def historical_value_str(self, satoshis, d_t):
        rate = self.history_rate(d_t)
        return self.value_str(satoshis, rate)
