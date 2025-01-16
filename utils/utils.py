from openai import OpenAI
import time
import pandas as pd
import requests
from groq import Groq
import openai
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

usBday = CustomBusinessDay(calendar=USFederalHolidayCalendar())


def getBuyDay(contractDate, prev)-> str:
    uBday = CustomBusinessDay(calendar=USFederalHolidayCalendar())
    contractDate = pd.Timestamp(contractDate)
    buyDay = contractDate - prev * uBday
    return buyDay.strftime('%Y-%m-%d')

def getTradingDay(date) -> str:
    us_business_day = CustomBusinessDay(calendar=USFederalHolidayCalendar())
    dateTime = pd.Timestamp(date)
    adjDate = dateTime if us_business_day.is_on_offset(dateTime) else dateTime + us_business_day
    return adjDate.strftime('%Y-%m-%d') 

def addUsBusinessDay():
    return CustomBusinessDay(calendar=USFederalHolidayCalendar())

client = OpenAI(api_key="")

def getTickerGPT(company):
    completion = client.chat.completions.create(
    model="gpt-4o",
            messages=[
            {
                "role": "system",
                "content": (
                    "You are a stock analyst identifying whether a given company, or its parent companies and subsidiaries, "
                    "are publicly traded.\n\n# Required Information:\n- Given company name.\n\n# Details to Include:\n"
                    "- Include parent or subsidiary companies of the given company, if they are publicly traded.\n"
                    "- Include the given company itself if it is publicly traded.\n\n# Output Format:\n"
                    "Provide a list of the companies separated by a comma of their TICKERS ONLY. Do not include further information "
                    "or notes. Do not output anything more than just the ticker, no explenation, no description, only the ticker. Output 'none' if the company is not publicly traded."
                )
            },
            {
                "role": "user",
                "content": company
            }
        ],
        temperature=1,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    
    return completion.choices[0].message.content

def getTickerLlma(company):
    response=""
    completion = client.chat.completions.create(
        model="llama3-groq-70b-8192-tool-use-preview",
        messages=[
            {
                "role": "system",
                "content": "You are a stock analyst identifying whether a given company, or its parent companies and subsidiaries, \"\n                    \"are publicly traded on american stock exchanges ONLY.\\n\\n# Required Information:\\n- Given company name.\\n\\n# Details to Include:\\n\"\n                    \"- Include parent or subsidiary companies of the given company, if they are publicly traded on a UNITED STATES STOCK EXCHANGE.\\n\"\n                    \"- Include the given company itself if it is publicly traded.\\n\\n# Output Format:\\n\"\n                    \"Provide a list of the companies separated by a comma of their TICKERS ONLY. Do not include further information \"\n                    \"or notes. Do not explain anything, the only output should be the ticker. Output 'none' if the company is not publicly traded.\""
            },
            {
                "role": "user",
                "content": company
            },
        ],
        temperature=0.5,
        max_tokens=1024,
        top_p=0.65,
        stream=True,
        stop=None,
    )
    
    for chunk in completion:
        if chunk.choices[0].delta and chunk.choices[0].delta.content:
            response+=(chunk.choices[0].delta.content)
    return response

def getPublicContractsLLM(df): 
    global contractColumns, apiCalls
    publicContracts =[]
    start = time.time()
    for i in range (len(df)):
        if apiCalls>30:
            end = time.time()
            intv = end - start 
            if intv < 60:
                time.sleep(100 - intv)
            
            start = time.time()
            apiCalls = 0
        ticker = getTickerLlma(df.iloc[i]["Recipient Name"])
        apiCalls+=1
        if ticker != "none": 
            df.loc[i, "Recipient Name"] = ticker
            publicContracts.append(df.iloc[i])
    
    return pd.DataFrame(publicContracts, columns=contractColumns).reset_index(drop=True, inplace=False)

import re 

def getPublicContractsGPT(contractDf):
    global contractColumns, progressPoints
    retries = 0

    print("started processing "+f"{contractDf}")
    
    publicContracts = []
    df = globals().get(contractDf)
    checkpoints = {int(len(df) * point): message for point, message in progressPoints.items()}

    for i in range(len(df)):
        if i in checkpoints:
            print(checkpoints[i])
        while retries<5: 
            try:
                ticker = getTickerGPT(df.iloc[i]['Recipient Name'])
                retries=0
                break
            except openai.RateLimitError as e:
                print(f"Rate limit exceeded")
                match = re.search(r"Please try again in (\d+(\.\d+)?)(ms|s)", str(e))
                if match: 
                    wait = float(match.group(1))
                    unit = match.group(3)
                    if unit == "ms":
                        wait /= 1000

                    print(f"Retrying after {wait:.2f} seconds...")
                    time.sleep(wait)
                    retries+=1 
                else: 
                    wait = min(10 * 2 ** retries, 60)
                    print(f"Retrying after {wait:.2f} seconds...")
                    time.sleep(wait)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                retries=0 
                break  

        if ticker != "none":
            df.at[i, 'Recipient Name'] = ticker 
            publicContracts.append(df.iloc[i])
        
    results = pd.DataFrame(publicContracts, columns=contractColumns).reset_index(drop=True, inplace=False)
    results.to_csv("/home/xikron/Projects/misc/data/"+contractDf+".csv", index=False)

    print(f"{contractDf} is done processing")


def setLinkIntd (ticker, start, end, freq):
    return f"https://financialmodelingprep.com/api/v3/historical-chart/{freq}/{ticker}?from={start}&to={end}&apikey=26srycwxWrFIhEuaZwic6mBdx7f4VjGT"

def setLinkEod (ticker, start, end):
    return f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={start}&to={end}&apikey=26srycwxWrFIhEuaZwic6mBdx7f4VjGT"

def setLinkRatios (ticker):
    return f"https://financialmodelingprep.com/api/v3/ratios/{ticker}?period=quarter&apikey=26srycwxWrFIhEuaZwic6mBdx7f4VjGT"

def setLinkCik (ticker):
    return f"https://financialmodelingprep.com/api/v4/mapper-cik-company/{ticker}?apikey=26srycwxWrFIhEuaZwic6mBdx7f4VjGT"

def getCik (ticker):
    response = requests.get(url=setLinkCik(ticker))
    if response.status_code == 200:
        cik = response.json()['companyCik'] or 0 
    else:
        cik =0
    return cik 

def setPayload(page):
    payload = {
    "subawards": False,
    "limit": 100,
    "page": page, 
    "filters": {
        "time_period": [
            {"start_date": "2007-10-01", "end_date": "2008-09-30"},
            {"start_date": "2008-10-01", "end_date": "2009-09-30"},
            {"start_date": "2009-10-01", "end_date": "2010-09-30"},
            {"start_date": "2010-10-01", "end_date": "2011-09-30"},
            {"start_date": "2011-10-01", "end_date": "2012-09-30"},
            {"start_date": "2012-10-01", "end_date": "2013-09-30"},
            {"start_date": "2013-10-01", "end_date": "2014-09-30"},
            {"start_date": "2014-10-01", "end_date": "2015-09-30"},
            {"start_date": "2015-10-01", "end_date": "2016-09-30"},
            {"start_date": "2016-10-01", "end_date": "2017-09-30"},
            {"start_date": "2017-10-01", "end_date": "2018-09-30"},
            {"start_date": "2018-10-01", "end_date": "2019-09-30"},
            {"start_date": "2019-10-01", "end_date": "2020-09-30"},
            {"start_date": "2020-10-01", "end_date": "2021-09-30"},
            {"start_date": "2021-10-01", "end_date": "2022-09-30"},
            {"start_date": "2022-10-01", "end_date": "2023-09-30"},
            {"start_date": "2023-10-01", "end_date": "2024-09-30"}, 
            {"start_date": "2024-10-01", "end_date": "2025-09-30"}
        ],
        "award_amounts": [{"lower_bound":"25000000"}],
        "award_type_codes": ["A", "B", "C", "D"],
        "naics_codes": [
            "11", "21", "22", "23", "31", "32", "33", "4233", "4235", "4238", "4246", "4247",
            "5111", "5112", "5121", "5122", "5151", "5152", "5161", "5171", "5172", "5173", "5174",
            "5175", "5179", "5181", "5182", "5191", "52", "54"
        ],
        "recipient_type_names": [
            "business", "corporate_entity_not_tax_exempt", "other_than_small_business",
            "subchapter_s_corporation", "partnership_or_limited_liability_partnership", 
            "limited_liability_corporation", "sole_proprietorship", "corporate_entity_tax_exempt", 
            "manufacturer_of_goods"
        ]
    },
    "fields": [
        "Award ID", "Recipient Name", "Award Amount", "Total Outlays", "Description", 
        "Contract Award Type", "def_codes", "COVID-19 Obligations", "COVID-19 Outlays", 
        "Infrastructure Obligations", "Infrastructure Outlays", "Awarding Agency", 
        "Awarding Sub Agency", "Start Date", "End Date", "recipient_id", "prime_award_recipient_id"
    ],
    "order": "desc",
    "sort": "Award Amount"
    }
    return payload