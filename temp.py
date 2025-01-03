import numpy as np
import pandas as pd
import requests
from datetime import datetime 
import matplotlib.pyplot as plt 
import math 
import time 
import uuid

from utils.utils import setLinkEod, setLinkIntd, getBuyDay, getTradingDay

contracts16 = pd.read_csv("data/portfolioTesting/c16.csv")
contracts16['Start Date']= pd.to_datetime(contracts16['Start Date'])
contracts16=contracts16.drop_duplicates(subset='Award ID').sort_values(by='Start Date')

from dataclasses import dataclass 
import uuid


# datastructure to track trades made on the same underlying via contractID 
@dataclass
class transaction: 
    contractID: int
    num: int

# globally unique id generator 
class uniqueId:
    def __init__(self):
        self.id = str(uuid.uuid4())

class BenchmarkPortfolio:
    """ a benchmarked portfolio that mimicks all trades from the strategy using the SP500 
        
        @c: starting capital 
        @w: percentage of capital allocated per trade 

        id: a unique 6 digit number to keep track of the portfolio when multithreading
        buys: a list of trades made on the SP500 
        valuation: tracks the value of the portfolio after each transaction 
        holds: flag to track if any pending assets need to be sold before next purcahse
        bankrupt: well... if the portfolio has sufficient funds to continue
    """

    def __init__(self, c, w):
        self.id = uniqueId().id
        self.capital = c
        self.weight = w
        self.trades = []
        self.valuation = [c]
        self.exceptions = []
        self.holds = False
        self.bankrupt = False
        
    def buy(self, pps, shares, id, buyDate):
        if self.capital >= pps*shares: 
            if self.holds == False:
                self.capital -= pps*shares
                self.trades.append(transaction(id, shares))
                self.valuation.append(self.capital)
                self.holds = True 
                print(f"B{shares}{'SPY'}{pps}D{buyDate}")

                return True 
            else: 
                print ("there are pending market positions to be cleared")
                return False 
        else: 
            print("insufficient capital to complete transaction")
            self.bankrupt = True   
            return False 

    def sell(self, pps, id, sellDate): 
        for transaction in reversed(self.trades):
            if transaction.contractID == id: 
                self.capital += transaction.num * pps 
                self.valuation.append(self.capital)
                print(f"S{transaction.num}{'SPY'}{pps}D{sellDate}")
                break 

    def sellSuccessful(self):
        self.holds = False

    def isClear (self):
        return not self.holds

    def logError (self, e, t, d, id, isSale, func): 
        """ logs exceptions in the portfolio's exceptions list and prints to CLI

            @e: the exception that was raised
            @t: the ticker of the underlying asset
            @d: the date of the transaction
            @id: the contractID that was being processed
            @isSale: boolean flag to indicate if the error was on a sell order
        """
        if isSale: 
            log = f"Unexpected error: {str(e)} when trying to sell at {func} for {t} on {d} via contractID: {id}"
        else:
            log = f"Unexpected error: {str(e)} on trying to buy at {func} for {t} on {d} via contractID: {id}"
        self.exceptions.append(log)
        print(log)

class Portfolio(BenchmarkPortfolio) : 
    """ a simulated portfolio that automatcally purchases and sells 
        assets using the government contracts + MR strategy 

        @z: mean reversion z-score treshold to sell
        @w: percentage of capital allocated to each trade 
        @c: starting capital

        trades: a dictionary to track all trades made on the same underlying
    """
    def __init__(self, z, w, c):
        super().__init__(c, w)
        self.trades = {}
        self.mRThresh = z

    def logTrade(self, ticker, id, shares): 
        if ticker not in self.trades: 
            self.trades[ticker] = [transaction(id, shares)]
        else: 
            self.trades[ticker].append(transaction(id, shares))
                        
    def buy(self, ticker, pps, shares, id, buyDate): 
        if self.capital >= pps*shares: 
            self.capital -= pps*shares
            self.logTrade(ticker, id, shares)
            #self.buys.append([transaction(id, shares), buyDate])
            self.holds = True
            self.valuation.append(self.capital)
            print(f"B{shares}{ticker}{pps}D{buyDate}")
            return True
        else: 
            print("insufficient capital to complete transaction")
            self.bankrupt = True   
            return False 
    
    def sell(self, pps, iD, ticker, sellDate): 
        if ticker in self.trades: 
            for transaction in self.trades[ticker]: 
                if transaction.contractID == iD: 
                    shares = transaction.num 
                    self.capital += shares * pps
                    self.trades[ticker].remove(transaction) 
                    print(f"B{shares}{ticker}{pps}D{sellDate}")

def getPricePerShare(p: BenchmarkPortfolio, t: str, date: str, id:str, isSale: bool):
    """ filters API calls to return the pps of the stock 45 minutes before closing on a given date, only 
        used for buy orders 
        requires: date is a us Trading Day

        @p: the portfolio object that is making the trade
        @t: stock ticker 
        @date: date of the trade
        @id: contractID triggering the trade 
        @isSale: flag to determine if the trade is a buy or sell
    """
    numtries = 0
    
    try:
        while numtries <= 3:
            response = requests.get(url=setLinkIntd(t, date, date, "5min"))

            if response.status_code == 200:
                try:
                    jsonData = response.json()
                    if len(jsonData) > 15:
                        pps = jsonData[-15]["open"]
                        return pps
                    elif len(jsonData) == 0:
                        response = requests.get(url=setLinkEod(t, date, date))
                        pps = response.json()['historical'][0]['close']
                        return pps
                except KeyError as e:
                     p.logError(e, t, date, id, isSale)
                     return None
                except Exception as e:
                    p.logError(e, t, date, id, isSale)
                    return None
            elif response.status_code == 429:
                time.sleep(60)
                print(f"Too many API calls exception, waiting until minute reset. current attempt: {numtries}")
                numtries += 1
            else:
                p.logError(response.status_code, t, date, id, isSale, "getPricePerShare")
                return None
    except Exception as e: 
            p.logError(e, t, date, id, isSale, "getPricePerShare")
            return None 
    
def getHistorical(p:BenchmarkPortfolio, t:str, s:str, e:str, id) -> pd.DataFrame:
    """ returns a pd.Dataframe of the opening prices of the stock over a given time period [s, e] 

        @p: the portfolio object making a trade 
        @t: stock ticker of the underlying
        @s: starting period
        @e: end 
        @id: contract id triggering the trade
    """
    
    numtries = 0

    try:
        while numtries <=3: 
            response = requests.get(url=setLinkIntd(t, s, e, "5min"))
            if response.status_code == 200: 
                data = response.json()
                if len(data)==0: 
                    print(data)
                    try:
                        response = requests.get(setLinkEod(t, s, e))
                        data = response.json()['historical']
                    except Exception as e: 
                        p.logError(e, t, s, id, True, "getHistorical")
                        return pd.DataFrame()
                if len(data)!= 0:
                    prices = pd.DataFrame([entry['close'] for entry in data])
                    return prices 
            elif response.status_code == 429: 
                time.sleep(60)
                print(f"Too many API calls exception, waiting until minute reset. current attempt: {numtries}")
                numtries +=1
            else: 
                p.logError(response.status_code, t, s, id, True, "getHistorical")
                return pd.DataFrame()              
    except Exception as e: 
        p.logError(e, t, s, id, True, "getHistorical")
        return pd.DataFrame() 
    
def meanReversion(miu, sigma, currentPps, zScore): 
    z = abs((miu-currentPps)/sigma)
    return z>=zScore

def getSellDay(p: BenchmarkPortfolio, ticker: str, date: str, zScore, id, window):
    startDay = getTradingDay(pd.to_datetime(date)-pd.Timedelta(days=window))
    endDay = getTradingDay(pd.to_datetime(date)-pd.Timedelta(days=1))
    currentDay = date

    historic = getHistorical(p, ticker, startDay, endDay, id)
    
    if (not historic.empty and len(historic)>= window): 
        sma = historic.rolling(window=window).mean()
        stDev = historic.rolling(window=window).std() 
        while True: 
            currentPps = getPricePerShare(p, ticker, currentDay, id, True)
            if meanReversion(sma, stDev, zScore, currentPps):
                return currentDay
            else: 
                currentDay = getTradingDay(pd.to_datetime(currentDay) + pd.Timedelta(days=1))
    else:
        return None 
    
def executeOrder(portfolio: Portfolio, benchPortfolio: BenchmarkPortfolio, w: float, ticker: str, date: str, id: int, isSale: bool) -> bool:
    """ executes a buy or sell order on the portfolio and benchmark portfolio 

        @portfolio: the strategy's portfolio to execute the order on 
        @benchPortfolio: the benchmark SPX portfolio to execute the order on 
        @w: the percentage of capital to allocate to the trade 
        @ticker: the ticker of the underlying asset 
        @date: the date of the trade 
        @id: the contractID triggering the trade 
        @isSale: flag to determine if the trade is a buy or sell
    """
    
    pps = getPricePerShare(portfolio, ticker, date, id, isSale)
    ppsSPX = getPricePerShare(benchPortfolio, "^SPX", date, id, isSale)

    if (pps!=None and ppsSPX!=None): 
        if not isSale:
            if (portfolio.isClear and benchPortfolio.isClear):
                shares = math.floor((w*portfolio.capital)/pps)
                sharesSPX = math.floor((w*benchPortfolio.capital)/ppsSPX)
                portfolio.buy(ticker, pps, shares, id, date)
                benchPortfolio.buy(ppsSPX, sharesSPX, id, date)            
                return True 
            else:
                return False 
        else: 
            portfolio.sell(pps, id, ticker, date)
            benchPortfolio.sell(pps, id, date)
            return True 
    return False 

def runPortfolio(contracts, z, w, c, bSig, window): 
    """ runs the portfolio simulation on the given contracts 

        @contracts: dataframe of contracts 
        @z: mean reversion z-score treshold
        @w: weight of total capital to allocate to each trade 
        @c: initial capital 
        @bSig: days before contract start date to buy
    """
    results = []
    strategyPortfolio = Portfolio(z, w, c)
    spxBenchmark = BenchmarkPortfolio(c, w)

    for i in range (len(contracts)):
        tick = contracts.iloc[i]['Recipient Name']
        contractStart = contracts.iloc[i]['Start Date']
        id = contracts.iloc[i]['internal_id']
        buyDay = getBuyDay(contractStart, bSig)
        if (executeOrder(strategyPortfolio, spxBenchmark, w, tick, buyDay, id, False)): 
            sellDay = getSellDay(strategyPortfolio, tick, buyDay, z, id, window)
            if (sellDay != None):
                if (executeOrder(strategyPortfolio, spxBenchmark, w, tick, sellDay, id, True)):
                    strategyPortfolio.sellSuccessful()
                    spxBenchmark.sellSuccessful()
                else: 
                    break
        else:
            break 
    """results.append(strategyPortfolio)
    results.append(spxBenchmark)
    return results"""

    temp = runPortfolio(contracts16, 1.5, 0.1, 100000000, 3, 20)