import numpy as np
import pandas as pd
import requests
from datetime import datetime 
import matplotlib.pyplot as plt 
import math 
import time 
import uuid

from utils.utils import setLinkEod, setLinkIntd, getBuyDay

contracts17 = pd.read_csv("data/portfolioTesting/c16.csv")
contracts17['Start Date']= pd.to_datetime(contracts17['Start Date'])
contracts17=contracts17.drop_duplicates(subset='Award ID').sort_values(by='Start Date')

from dataclasses import dataclass 
import uuid
exceptions = []

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
        
        @params c: starting capital 
        @params w: percentage of capital allocated per trade 

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
        self.holds = False
        self.bankrupt = False
        self.exeptions = []
        
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

class Portfolio(BenchmarkPortfolio) : 
    """ a simulated portfolio that automatcally purchases and sells 
        assets using the government contracts + MR strategy 

        @params z: mean reversion z-score treshold to sell
        @params w: percentage of capital allocated to each trade 
        @params c: starting capital

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
            if self.holds == False: 
                self.capital -= pps*shares
                self.logTrade(self, self.trades, ticker, id, shares)
                self.buys.append([transaction(id, shares), buyDate])
                self.holds = True
                self.valueation.append(self.capital)
                print(f"B{shares}{ticker}{pps}D{buyDate}")
                return True
            else: 
                print ("there are pending market positions to be cleared")
                return False 

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

def logError (e, contractID, date, isSale, ticker): 
    """ logs exceptions in the global exceptions list and prints to CLI

        @params e: the exception that was raised
        @params contractID: the contractID that was being processed
        @params date: the date of the transaction
        @params isSale: boolean flag to indicate if the error was on a sell order
        @params ticker: the ticker of the underlying asset
    """
    global exceptions
    if isSale: 
        log = f"Unexpected error: {str(e)} on sell order of {ticker} on {date} via contractID: {contractID}"
    else:
        log = f"Unexpected error: {str(e)} on buy order of {ticker} on {date} via contractID: {contractID}"
    exceptions.append(log)
    print(log)

def getPricePerShare(ticker, date, id, isSale):
    """ filters API calls to return the pps of the stock 45 minutes before closing on a given date,  
        
        @params ticker: stock ticker 
        @params date: date of the trade
        @params id: contractID triggering the trade 
        @params isSale: flag to determine if the trade is a buy or sell
    """
    global exceptions
    numtries = 0

    while numtries <= 3:
        response = requests.get(url=setLinkIntd(ticker, date, date, "5min"))

        if response.status_code == 200:
            try:
                json_data = response.json()
                if len(json_data) == 0:
                    response = requests.get(url=setLinkEod(ticker, date, date))
                    pps = response.json()['historical'][0]['close']
                    return pps
                elif len(json_data) > 15:
                    pps = json_data[-15]["open"]
                    return pps
            except Exception as e:
                logError(e, id, date, isSale, ticker)
                return None
        elif response.status_code == 429:
            time.sleep(60)
            print(f"Too many API calls exception, waiting until minute reset. current attempt: {numtries}")
            numtries += 1
        else:
            logError(response.status_code, id, date, isSale, ticker)
            return None
    return None

def meanReversion(): 
    pass 

def getSellDay(date, zScore, ticker):
    pass

def executeOrder(portfolio, benchPortfolio, w, ticker, date, id, isSale): 
    """ executes a buy or sell order on the portfolio and benchmark portfolio 

        @params portfolio: the portfolio to execute the order on 
        @params benchPortfolio: the benchmark portfolio to execute the order on 
        @params w: the percentage of capital to allocate to the trade 
        @params ticker: the ticker of the underlying asset 
        @params date: the date of the trade 
        @params id: the contractID triggering the trade 
        @params isSale: flag to determine if the trade is a buy or sell
    """
    global exceptions 
    
    pps = getPricePerShare(ticker, date, id, isSale)
    ppsSPX = getPricePerShare("^SPX", date, id, isSale)

    if (pps!=None and ppsSPX!=None): 
        if isSale:
            shares = math.floor((w*portfolio.capital)/pps)
            sharesSPX = math.floor((w*benchPortfolio.capital)/ppsSPX)
            portfolio.buy(ticker, pps, shares, id, date)
            benchPortfolio.buy(ppsSPX, sharesSPX, id, date)            
            return True 
        else: 
            portfolio.sell(pps, id, ticker, date)
            benchPortfolio.sell(pps, id, date)
            portfolio.sellSuccessful()
            benchPortfolio.sellSuccessful()
            return True 
    else:
        return False
    
def runPortfolio(contracts, z, w, c, bSig): 
    """ runs the portfolio simulation on the given contracts 

        @params contracts: dataframe of contracts 
        @params z: mean reversion z-score treshold
        @params w: weight of total capital to allocate to each trade 
        @params c: initial capital 
        @params bSig: days before contract start date to buy
    """
    global exceptions 
    strategyPortfolio = Portfolio(z, w, c)
    spxBenchmark = BenchmarkPortfolio(c, w)

    for i in range (len(contracts)):
        tick = contracts.iloc[i]['Recipient Name']
        contractStart = contracts.iloc[i]['Start Date']
        id = contracts.iloc[i]['internal_id']
        buyDay = getBuyDay(contractStart, bSig)
        if (executeOrder(strategyPortfolio, spxBenchmark, w, tick, buyDay, id, False)): 
            sellDay = getSellDay(buyDay, z, tick)
            executeOrder(strategyPortfolio, spxBenchmark, w, tick, contractStart, id, True)
        else:
            break 