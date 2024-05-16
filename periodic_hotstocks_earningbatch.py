# Util 함수들
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles
import numpy as np 
import random
import httpx
import json 
import os
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib
matplotlib.use('Agg')
#금융관련 APIs
from openai import OpenAI
import finnhub
from groq import Groq
import yfinance as yf
#private made 파일
import config
import utilTool


# API KEY 설정
client = OpenAI(api_key = config.OPENAI_API_KEY)
rapidAPI = config.RAPID_API_KEY
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
groq_client = Groq(api_key=config.GROQ_CLOUD_API_KEY)
logging.basicConfig(level=logging.DEBUG)

##################################################################################################################################
#@@ 기능정의 : hot trend 해외종목 25여개에 대해서 종목뉴스를 미리 호출하고, 이들에 대한 Earning정보를 미리 생성하는 배치 by son (24.04.28)
#@@ Logic   : 1. yahoo finance 의 most active 종목 25개 페이지를 크롤링 해와서 종목들을 list up 시킴
#@@           2. seeking alpah 종목뉴스(by RapidAPI)를 이용하여 해당 종목들의 뉴스 20개를 가져와서 json으로 저장시킴
#@@              (**파일명 :: batch/stocknews/종목코드/news_종목코드_{todayDate}.json)               
#@@           3. 개별 종목뉴스에 대한 AI의 요약 및 의견 파일을 GPT를 활용하여 생성시킴 
#@@              (**파일명 :: batch/stocknews/종목코드/aisummary_종목코드_{todayDate}.txt)
#@@           4. 종목 뉴스의 AI기사분석 데이터까지 저장 (Link 이용)
#@@              (**파일명 :: batch/stocknews/종목코드/news_뉴스아이디.json )
#@@         ** → 최종적으로 파일들을  frStockinfo.js 에서 불러와서 사용한다. (*떨궈진 파일이 있는경우 파일데이터로 선 호출) 
##################################################################################################################################

# 야후 인기 종목들 가져옴
async def scrape_and_save_stocks(client):
    url = 'https://finance.yahoo.com/most-active'
    try:
        response = await client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        symbols = [link.text.strip() for link in soup.select('a[data-test="quoteLink"]')]

        async with aiofiles.open('batch/hotstocks_earning.txt', 'w') as file:
            await file.write('\n'.join(symbols))
        print("Stocks data saved successfully.")
        return True
    except Exception as e:
        print(f"웹 크롤링 중 오류 발생: {e}")
        return False
    
# 혹시 수동으로 종목을 입력해서 가져와야될 경우도 있을것 같아, 파일로 먼저 저장하고, 이후 읽어오는 2단계로 변경함. 
async def load_stocks_from_file():
    try:
        # 두 파일의 경로를 리스트로 관리
        files = ['batch/hotstocks_manual.txt', 'batch/hotstocks_earning.txt']
        symbols_set = set()  # 중복을 제거하기 위한 세트

        # 각 파일을 순회하면서 데이터 읽기
        for file_path in files:
            async with aiofiles.open(file_path, 'r') as file:
                symbols = await file.read()
                symbols_set.update(symbols.splitlines())  # 세트에 추가하면서 자동 중복 제거

        print("Stocks data loaded successfully.")
        return list(symbols_set)  # 세트를 리스트로 변환하여 반환
    except Exception as e:
        print(f"파일 읽기 실패: {e}")
        return []    
  
  
#[1. 차트 이미지 떨구기] ##################################################### 
async def get_both_charts(ticker: str):
    try:    
        # Generate charts for each symbol
        fig1 = await get_historical_eps(ticker)
        earnings_chart_base64 = utilTool.get_chart_base64(fig1) if fig1 is not None else None
       
        fig2 = await get_recommend_trend(ticker)
        recommendations_chart_base64 = utilTool.get_chart_base64(fig2) if fig2 is not None else None

        todayDate = datetime.now().strftime("%Y%m%d")
        directory = f'batch/earning_data/{ticker}'
        os.makedirs(directory, exist_ok=True)

        # Only save the chart data if charts are generated
        if earnings_chart_base64 is not None or recommendations_chart_base64 is not None:
            file_path = f'{directory}/earningChart_{ticker}_{todayDate}.json'
            async with aiofiles.open(file_path, 'w') as file:
                await file.write(json.dumps({
                    "earnings_chart": earnings_chart_base64,
                    "recommendations_chart": recommendations_chart_base64
                }))
        else:
            print(f"No chart data available to save for {ticker}.")
    except Exception as e:
        print(f"An error occurred while processing charts for {ticker}: {e}")
        return None


async def get_historical_eps(ticker, limit=4):
    try:
        earnings = finnhub_client.company_earnings(ticker, limit)
        if not earnings:  
            print(f"No earnings data available for {ticker}")
            return None  
        earnings_json = [
            {
                "period":earning["period"],
                "actual":earning["actual"],
                "estimate":earning["estimate"],
                "surprisePercent":earning["surprisePercent"]
            } for earning in earnings 
        ]
        earnings_json.sort(key = lambda x:x['period'])
        df_earnings=pd.DataFrame(earnings_json)
        
        fig, ax = plt.subplots(figsize=(8,5))
        ax.scatter(df_earnings['period'], df_earnings['actual'],c='green', s=500, alpha=0.3, label='actual')
        ax.scatter(df_earnings['period'], df_earnings['estimate'],c='blue', s=500, alpha=0.3, label='estimate')
        ax.set_xlabel('announcement date', fontsize=15)
        ax.set_ylabel('eps', fontsize=15)
        ax.set_title('{} - Historical eps Surprise'.format(ticker), fontsize=17)
        ax.grid()
        ax.legend()

        for i in range(len(df_earnings)):
            plt.text(df_earnings['period'][i], df_earnings['actual'][i], ('Missed by ' if df_earnings['surprisePercent'][i] <0 else 'Beat by ')+ "{:.2f}".format(df_earnings['surprisePercent'][i])+"%",
                    color='black' if df_earnings['surprisePercent'][i] <0 else 'red' , fontsize=11, ha='left', va='bottom')
        return fig
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
async def get_recommend_trend (ticker) : 
    recommend_trend = finnhub_client.recommendation_trends(ticker)
    df_recommend_trend = pd.DataFrame(recommend_trend).set_index('period').drop('symbol', axis=1).sort_index()

    fig, ax = plt.subplots(figsize=(8,5))
    width = 0.6  
    
    bottom=np.zeros(len(df_recommend_trend))
    p1= ax.bar(df_recommend_trend.index,  df_recommend_trend['strongSell'], label='strong Sell', color='red', width=width, bottom=bottom)
    bottom +=df_recommend_trend['strongSell']
    p2= ax.bar(df_recommend_trend.index,  df_recommend_trend['sell'], label='Sell', color='orange',width=width,bottom=bottom)
    bottom +=df_recommend_trend['sell']
    p3= ax.bar(df_recommend_trend.index,  df_recommend_trend['hold'], label='Hold', color='grey',width=width,bottom=bottom)
    bottom +=df_recommend_trend['hold']
    p4= ax.bar(df_recommend_trend.index,  df_recommend_trend['buy'], label='Buy', color='skyblue',width=width,bottom=bottom)
    bottom +=df_recommend_trend['buy']
    p5= ax.bar(df_recommend_trend.index,  df_recommend_trend['strongBuy'], label='strong Buy', color='blue',width=width,bottom=bottom)
    
    if df_recommend_trend['strongSell'].sum() > 0 :
        ax.bar_label(p1, label_type='center')
    if df_recommend_trend['sell'].sum() > 0 :
        ax.bar_label(p2, label_type='center')
    if df_recommend_trend['hold'].sum() > 0 :
        ax.bar_label(p3, label_type='center')
    if df_recommend_trend['buy'].sum() > 0 :
        ax.bar_label(p4, label_type='center')
    if df_recommend_trend['strongBuy'].sum() > 0 :
        ax.bar_label(p5, label_type='center')
    
    plt.title('{} recommendation trend'.format(ticker), fontsize=12)
    plt.ylabel('Number of analysts')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
    return fig


#[2.실적발표 테이블 만들기] ##################################################### 

def get_news (ticker, Start_date, End_date, count=20):
    news=finnhub_client.company_news(ticker, Start_date, End_date)
    if len(news) > count :
        news = random.sample(news, count)
    sum_news = ["<li><h4>{} </h4><p>{}</p></li> \n".format(n['headline'], n['summary']) for n in news]
    sum_news.insert(0, "<ul class='newsanalysis-list'>")
    sum_news.append("</ul>")  
    return sum_news 

def gen_term_stock (ticker, Start_date, End_date):
    df = yf.download(ticker, Start_date, End_date)['Close']
    term = '상승하였습니다' if df.iloc[-1] > df.iloc[0] else '하락하였습니다'
    terms = '{}부터 {}까지 {}의 주식가격은, $ {}에서 $ {}으로 {}. 관련된 뉴스는 다음과 같습니다.'.format(Start_date, End_date, ticker, int(df.iloc[0]), int(df.iloc[-1]), term)
    return terms 

# combine case1 and case2 
def get_prompt_earning (ticker):
    prompt_news_after7 = ''
    curday = utilTool.get_curday()
    profile = finnhub_client.company_profile2(symbol=ticker)
    
    company_template = "[기업소개]:\n{name}은 {ipo}에 상장한 {finnhubIndustry}섹터의 기업입니다.\n"
    intro_company = company_template.format(**profile)    
    
    # find announce calendar 
    Start_date_calen = (datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d") # 현재 시점 - 3개월 
    End_date_calen = (datetime.strptime(curday, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")  # 현재 시점 + 1개월 
    # 데이터 안와서 에러나는 종목들이 있어서 로직 수정
    finnhub_data = finnhub_client.earnings_calendar(_from=Start_date_calen, to=End_date_calen, symbol=ticker, international=False).get('earningsCalendar')
    date_announce, eps_actual, eps_estimate, earning_y, earning_q, revenue_estimate = None, np.nan, np.nan, None, None, np.nan
    # 데이터 있을때만 처리한다
    if finnhub_data and len(finnhub_data) > 0:
        announce_calendar = finnhub_data[0]
        date_announce = announce_calendar.get('date')
        eps_actual = announce_calendar.get('epsActual', np.nan)
        eps_estimate = announce_calendar.get('epsEstimate', np.nan)
        earning_y = announce_calendar.get('year')
        earning_q = announce_calendar.get('quarter')
        revenue_estimate_raw = announce_calendar.get('revenueEstimate')
        if revenue_estimate_raw is not None:
            revenue_estimate = round(revenue_estimate_raw / 1000000, 2)
        else:
            revenue_estimate = np.nan
    else:
        print("No earnings announcement data available for this ticker.")
       
    if  eps_actual is None or np.isnan(eps_actual):  # [Case2] 실적발표 전 
        # create Prompt 
        head = "{}의 {}년 {}분기 실적 발표일은 {}으로 예정되어 있습니다. 시장에서 예측하는 실적은 매출 ${}M, eps {}입니다. ".format(profile['name'], earning_y,earning_q, date_announce, revenue_estimate, eps_estimate)
        if all(utilTool.is_valid(value) for value in [earning_y, earning_q, date_announce, revenue_estimate, eps_estimate]):
            head2 = "{}의 {}년 {}분기 실적 발표일은 <span style='color: #e7536d'>{}</span>일로 예정되어 있습니다. 시장에서 예측하는 실적은 매출 ${}M, eps {}입니다.".format(profile['name'], earning_y, earning_q, date_announce, revenue_estimate, eps_estimate)

        else : head2 = ""
            
        # [case2] 최근 3주간 데이터 수집  
        Start_date=(datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        End_date=curday
        
        # 뉴스 수집 및 추출 
        news = get_news (ticker, Start_date, End_date)
        terms_ = gen_term_stock(ticker, Start_date, End_date)
        prompt_news = "최근 3주간 {}: ".format(terms_)
        for i in news:
            prompt_news += "\n" + i 
        
        info = intro_company + '\n' + head 
        cliInfo = intro_company + '\n' + head2 +'\n'
        prompt = info + '\n' + prompt_news + '\n' + f"\n\n Based on all the information (from {Start_date} to {End_date}), let's first analyze the positive developments, potential concerns and stock price predictions for {ticker}. Come up with 5-7 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Finally, make your prediction of the {ticker} stock price movement for next month. Provide a summary analysis to support your prediction."    
        SYSTEM_PROMPT = "You are a seasoned stock market analyst working in South Korea. Your task is to list the positive developments and potential concerns for companies based on relevant news and stock price of target companies, \
            Then, make analysis and prediction for the companies' stock price movement for the upcoming month. Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Prediction & Analysis]:\n...\n\n  Because you are working in South Korea, all responses should be done in Korean not in English. \n "
    
    else : # [Case1] 실적발표 후
    
        # get additional information         
        excess_eps = round(abs(eps_actual / eps_estimate -1)* 100,1)
        revenue_actual=round(announce_calendar.get('revenueActual')/1000000)
        excess_revenue = round(abs(revenue_actual/revenue_estimate-1)*100,1)
        
        
        # create Prompt 
        term1 = '상회하였으며' if revenue_actual > revenue_estimate else '하회하였으며'
        term2 = '상회하였습니다.' if eps_actual > eps_estimate else '하회하였습니다'
        head = "\n [실적발표 요약]: \n {}에 {}년{}분기 {}의 실적이 발표되었습니다. 실적(매출)은 ${}M으로 당초 예측한 ${}M 대비 {}% {}, eps는 예측한 {}대비 {}으로 eps는 {}% {} ".format(date_announce,earning_y,earning_q, profile['name'], revenue_actual, revenue_estimate,excess_revenue,term1,eps_estimate, eps_actual, excess_eps, term2)
        if all(utilTool.is_valid(value) for value in [date_announce, earning_y, earning_q, profile['name'], revenue_actual, revenue_estimate, excess_revenue, term1, eps_estimate, eps_actual, excess_eps, term2]):
            head2 = "\n [실적발표 요약]: \n {}에 {}년{}분기 {}의 실적이 발표되었습니다. 실적(매출)은 ${}M으로 당초 예측한 ${}M 대비 {}% {}, eps는 예측한 {}대비 {}으로 eps는 {}% {}".format(date_announce, earning_y, earning_q, profile['name'], revenue_actual, revenue_estimate, excess_revenue, term1, eps_estimate, eps_actual, excess_eps, term2)
        else:
            head2 = ""
        
        
        # 기준점 산출 (세가지 시점)
        Start_date_before=(datetime.strptime(date_announce, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        End_date_before=(datetime.strptime(date_announce, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        Start_date_after = date_announce
        if datetime.strptime(curday, "%Y-%m-%d") < (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)):
            End_date_after = curday
        else :
            Start_date_after = date_announce
            End_date_after = (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            Start_date_after7 = (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            End_date_after7 = curday
        
        # 뉴스 수집 및 추출 (세가지 구간)
        news_before = get_news (ticker, Start_date_before, End_date_before)
        terms_before = gen_term_stock(ticker, Start_date_before, End_date_before)
        prompt_news_before = "Earning call 전, {}: \n\n ".format(terms_before)
        for i in news_before:
            prompt_news_before += "\n" + i 
        
        news_after = get_news (ticker, Start_date_after, End_date_after)
        terms_after = gen_term_stock(ticker, Start_date_after, End_date_after)
        prompt_news_after = "Earning call 후, {}: \n\n ".format(terms_after)
        for i in news_after:
            prompt_news_after += "\n" + i 

        
        if datetime.strptime(curday, "%Y-%m-%d") > (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)):
            news_after7 = get_news (ticker, Start_date_after7, End_date_after7)
            terms_after7 = gen_term_stock(ticker, Start_date_after7, End_date_after7)
            prompt_news_before = "Earning call 발표 7일 이후, {}: \n\n ".format(terms_after7)
            for i in news_after7:
                prompt_news_after7 += "\n" + i 
        else :
            prompt_news_after7 = 'Not enough time since the earnings announcement to monitor trends'
            
        
        info = intro_company + '\n' + head 
        cliInfo = intro_company + '\n' + head2
        prompt_news = prompt_news_before + '\n' + prompt_news_after + '\n' + prompt_news_after7  
        prompt = info + '\n' +  prompt_news + '\n' + f"\n\n Based on all the information before earning call (from {Start_date_before} to {End_date_before}), let's first analyze the positive developments, potential concerns and stock price predictions for {ticker}. Come up with 5-7 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Then, based on all the information after earning call (from {date_announce} to {curday}), let's find 5-6 points that meet expectations and points that fall short of expectations when compared before the earning call. " \
        f"Finally, make your prediction of the {ticker} stock price movement for next month. Provide a summary analysis to support your prediction."    
        
        SYSTEM_PROMPT = "You are a seasoned stock market analyst working in South Korea. Your task is to list the positive developments and potential concerns for companies based on relevant news and stock price before an earning call of target companies, \
            then provide an market reaction with respect to the earning call. Finally, make analysis and prediction for the companies' stock price movement for the upcoming month. Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Market Reaction After Earning Aall]:\n[Prediction & Analysis]:\n...\n\n  Because you are working in South Korea, all responses should be done in Korean not in English. \n "

    return cliInfo, info, prompt_news, prompt, SYSTEM_PROMPT

def query_gpt4(ticker: str):
    # get_prompt_earning 함수로부터 4개의 값을 올바르게 받음
    cliInfo, info, prompt_news, prompt, SYSTEM_PROMPT = get_prompt_earning(ticker)

    # OpenAI GPT-4 호출
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    completion_content = completion.choices[0].message.content if completion.choices else "No completion found."
    # FastAPI 클라로 보내기 위해 JSON으로 변환하여 반환
    return {
        "info": cliInfo,
        "prompt_news": prompt_news,
        "completion": completion_content
    }

async def get_analysis(ticker: str):
    result = query_gpt4(ticker)
    todayDate = datetime.now().strftime("%Y%m%d")
    directory = f'batch/earning_data/{ticker}'
    os.makedirs(directory, exist_ok=True)
    file_path = f'{directory}/gptAnalysis_{ticker}_{todayDate}.json'
    async with aiofiles.open(file_path, 'w') as file:
        await file.write(json.dumps(result))

               
async def main():
    timeout_config = httpx.Timeout(10000.0)
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        await handle_earning_batch(client)

async def handle_earning_batch(client):
    success = await scrape_and_save_stocks(client)
    if success:
        symbols = await load_stocks_from_file()
        for symbol in symbols:
            try:
                await get_both_charts(symbol)
                await get_analysis(symbol)
            except Exception as e:
                print(f"An error occurred while processing {symbol}: {e}")
                continue  

if __name__ == "__main__":
    asyncio.run(main())

#print(fetch_news_finnhub('AAPL'))