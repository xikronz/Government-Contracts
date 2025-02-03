# Event driven trading: a Mean Reversion-Based Sell strategy triggered by Governent Contracts
Every year, the United-States Federal Government spends over **$600 Billion** on contracting projects with large-cap, mid-cap and small-cap businesses, making it one of the most lucrative expenditures in the global economy. Over the past decade, an avergage of **57.31%** of it's top 100 recipients were corporations that are **publically traded** on US stock exchanges. 

Despite the scale of these expenditures, retail investors often overlook federal contracting trends as a factor in stock selection. Many firms receive billions in government contracts annually, securing stable revenue streams that can mitigate risk during economic downturns and enhance long-term growth prospects. In section 5, **capital allocation**, we go over how the expected impact of a contract is evaluated using a **sigmoid composition** of forward $\Delta$ EBITDA, $\Delta$ margins, $\Delta$ cash flow etc... projections. 

Our methodology prioritizes:

- Contract Volume & Value – Companies with a history of securing high-dollar federal contracts.
- Sector Analysis – Focus on industries that receive significant government funding, such as defense, technology, and infrastructure.
- Stock Performance & Fundamentals – Evaluating financial stability, revenue growth, and profitability alongside contract awards.

With final normalized **annual returns of 189.6%**, Sharpe ratio of 5.852, and maximum drawdown of 7.52% despite periods of market recession, the strategy demonstrated robust risk-adjusted performance while maintaining relatively low drawdowns and indicates high potential for further research.

*All raw trades follow [orderType-numShares-TICK-pps-date-portfolioValue]* 

# Behind the Scenes of a Multi-Billion Dollar Operation 
![Screenshot from 2024-12-25 22-30-37](https://github.com/user-attachments/assets/7d77d509-43d3-443f-8833-83c3691804a8)

# Backtested Returns FY16-FY19, FY23 
All portfolios recieved input params from the constructor of (z, w, c) = (100000000, 0.1, 2.5) and were executed in parallel where 
- z: mean reversion z-score treshold to sell
- w: lower bound percentage of capital allocated to each trade 
- c: starting capital
  
## Spotlight performance
As economic conditions stabilized from the COVID-19 recession, companies were able to execute on pending contracts at scale, driving revenue growth and stock appreciation, which in turn contributed to the portfolio’s exceptional performance in 2023. The highest earning single trade being a +11.23% on 8542116 shares of LDOS @95.06/share on 11-10-2013, exposing 10% of the portfolio until 22-11-2013 when positions closed @106.12/share.

![Screenshot from 2025-02-03 11-18-08](https://github.com/user-attachments/assets/6a41d91d-423b-4033-ba90-e4334e740e09)

## Returns over FY16-19
Although 2018 presented challenges, with a negative Sharpe ratio (-0.6712) and a maximum drawdown of -20.41%, the strategy closed in the money at +94.75% while navigating a bearish market.
![Screenshot from 2025-02-03 10-43-02](https://github.com/user-attachments/assets/a4008c6e-a9ba-4a24-8811-4dc4a8c45e9a)

# Strategy at a Glance 
![Screenshot from 2025-02-03 10-40-26](https://github.com/user-attachments/assets/6f6047b0-8981-4feb-8430-2a1892137ebb)

# Strategy risks and remarks
![Screenshot from 2025-02-03 11-56-07](https://github.com/user-attachments/assets/2b139f27-1fb8-4c04-93ed-287dd96e5dc4)



