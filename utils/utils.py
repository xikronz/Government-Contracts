from openai import OpenAI
import time
import pandas as pd
from groq import Groq
import openai

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
    link="https://financialmodelingprep.com/api/v3/historical-chart/"+freq+"/"+ticker+"?from="+start+"&to="+end+"&apikey="
    return link

def setLinkEod (ticker, start, end):
    return"https://financialmodelingprep.com/api/v3/historical-price-full/"+ticker+"?from="+start+"&to="+end+"&apikey="
