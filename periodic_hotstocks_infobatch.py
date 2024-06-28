# Util 함수들
import asyncio
import logging
from datetime import datetime, timedelta
import aiofiles
import httpx
import json 
import os
import numpy as np 
import markdown
import re
#금융관련 APIs
from openai import OpenAI
from serpapi import GoogleSearch
import yfinance as yf
import finnhub
from groq import Groq
#private made 파일
import config
import utilTool
#langchain 관련
from langchain_community.document_loaders.web_base import WebBaseLoader
from langchain.chains import LLMChain

# API KEY 설정
client = OpenAI(api_key = config.OPENAI_API_KEY)
groq_client = Groq(api_key=config.GROQ_CLOUD_API_KEY)
logging.basicConfig(level=logging.DEBUG)

##################################################################################################################################
#@@ 기능정의 : 종목들에 대한 기본정보를 미리 생성하는 배치 by son (24.05.15) 
#@@ Logic   : AI가 말해주는 주식정보[해외] > Stock Info(종목 데이터) 첫 부분에 미리 보여준다. 
#@@             * 기존에 periodic_hotstock* 다른 배치파일에서 만든 batch/hotstocks.txt, hostocks_manual.txt 종목들을 대상으로 함. 
#@@           1. 종목 코드로 종목이름 찾아옴 (yFinance)
#@@              - 회사 기본 정보 몇개도 같이 불러옴 
#@@           2. serpAPI - finance API 로 해당 종목정보 1차 로딩 
#@@           3. serpAPI - google News API 로 해당 종목정보 2차 로딩
#@@           4. GPT를 이용해 이를 전체적으로 요약 정리시킴 
#@@              (**파일명 :: batch/stocknews/{ticker}/{ticker}_basicinfo_{오늘날짜}.txt )
#@@         ** → 최종적으로 파일들을  frStockinfo.js 에서 불러와서 사용한다. (*떨궈진 파일이 있는경우 파일데이터로 선 호출) 
##################################################################################################################################


async def load_stocks_from_file():
    try:
        files = ['batch/hotstocks_manual.txt', 'batch/hotstocks.txt']
        symbols_set = set()

        for file_path in files:
            async with aiofiles.open(file_path, 'r') as file:
                symbols = await file.read()
                symbols_set.update(symbols.splitlines())

        print("Stocks data loaded successfully.")
        return list(symbols_set)
    except Exception as e:
        print(f"파일 읽기 실패: {e}")
        return []
    
async def get_news_info(ticker):
    params = {
    "engine": "google_news",
    "q": ticker,
    "api_key": config.SERPAPI_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    news_results = results["news_results"]
    #print("************news_results***************************")
    #print(news_results)
    #print("***************************")          
    return news_results    
  

async def get_finance_info(ticker):
    params = {
        "engine": "google_finance",
        "q": ticker,
        "api_key": config.SERPAPI_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    #print("***************************")
    #print(results)
    #print("***************************")
    return results
       

async def get_all_info_together(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    company_name = info.get('shortName')
    finance_info = await get_finance_info(ticker)     
    news_info = await get_news_info(company_name)   
    basic_info = {
        'company_info': {
            'company name': info.get('shortName'),
            'company sector': info.get('sector'),
            'current stock price': info.get('currentPrice', np.nan),
            '50일 평균가': info.get('fiftyDayAverage'),
            '52주 신고가': info.get('fiftyTwoWeekHigh'),
            '52주 신저가': info.get('fiftyTwoWeekLow'),
            'market cap': info.get('marketCap'),
            'total debt': info.get('totalDebt', np.nan),
            'operating cashflow': info.get('operatingCashflow', np.nan)
        }
    }
    return basic_info, finance_info, news_info 

       
# GPT4 에 뉴스요약을 요청하는 공통함수
async def get_data_from_gpt(prompt):
    try:
        SYSTEM_PROMPT = '''You are an expert economist and news analyst. You will provide basic information and news data about a specific company. 
        Utilizing this, please describe the general information and current situation of the company. 
        As a financial expert, connect various pieces of information to neatly summarize and explain objective and insightful information. 
        For news-related content, write 3-4 lines in the form of "Recently, there was this news." 
        Please provide insightful and in-depth content by linking it with basic company information. Be sure to explain in Korean. 
        Also, do not provide any other responses besides the requested content.
        Since this content will be displayed on a web page, it's okay to include some HTML tags for font color and other formatting to enhance readability.'''        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in gpt4_news_sum function: %s", str(e))
        return None

# Lama3 API로도 TEST 해보기
async def get_data_from_lama(prompt):
    try:
        SYSTEM_PROMPT = '''You are an expert economist and news analyst. You will provide basic information and news data about a specific company. 
        Utilizing this, please describe the general information and current situation of the company. 
        As a financial expert, connect various pieces of information to neatly summarize and explain objective and insightful information. 
        For news-related content, write 3-4 lines in the form of "Recently, there was this news." 
        Please provide insightful and in-depth content by linking it with basic company information. Be sure to explain in Korean. 
        Also, do not provide any other responses besides the requested content.
        Since this content will be displayed on a web page, it's okay to include some HTML tags for font color and other formatting to enhance readability.'''      
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ],
            #model="mixtral-8x7b-32768",
            model="llama3-8b-8192",            
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in lama3_news_sum function: %s", str(e))
        return None
       		
def add_target_blank_and_underline(html_string):
    """뉴스 데이터 markdown에서 html로 바꿀 때 a태그에 target="_blank"와
    "text-decoration: underline" 추가하는 함수 """
    
    # <a> 태그를 찾는 정규 표현식
    pattern = r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"([^>]*)>(.*?)<\/a>'
    
    def replace_link(match):
        href = match.group(1)
        attrs = match.group(2)
        text = match.group(3)
        
        # 이미 target="_blank"가 없으면 추가
        if 'target="_blank"' not in attrs:
            attrs += ' target="_blank"'
        
        # text-decoration: underline 추가
        if 'text-decoration:' not in attrs:
            attrs += ' style="text-decoration: underline;"'
        
        # 수정된 <a> 태그 반환
        return f'<a href="{href}"{attrs}>{text}</a>'
    
    # 매칭된 모든 <a> 태그에 대해 함수를 적용하여 수정
    modified_html = re.sub(pattern, replace_link, html_string)
    return modified_html 
   
async def save_summary_to_file(directory, ticker, summary):
    print(summary)
    summary = markdown.markdown(summary)
    todayDate = datetime.now().strftime("%Y%m%d")
    os.makedirs(directory, exist_ok=True)
    filename = f"{ticker}_basicinfo_{todayDate}.txt"
    filepath = os.path.join(directory, filename)
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(add_target_blank_and_underline(summary))

async def process_ticker(ticker):
    try:
        basic_info, finance_info, news_info = await get_all_info_together(ticker)
        prompt = f'''You are a financial expert and analyst. I will provide you with information about a specific corporation.
        Please review the data and organize it neatly and systematically. 
        Analyze various financial data to explain the company in a comprehensive and in-depth manner from multiple perspectives, and provide additional insightful commentary
        on the news data as well. 
        It would be even better if you could analyze the news data alongside the current finance data and provide insights into future prospects, trends, and possibilities as a financial expert. 
        [data start]
        1. Basic Company Information: {basic_info}
        2. Company Financial Information: {finance_info}
        3. News Data: {news_info}'''
        result = await get_data_from_gpt(prompt)
        #print(result)
        directory = f'batch/stocknews/{ticker}'
        await save_summary_to_file(directory, ticker, result)
    except Exception as e:
        print(f"Failed to process {ticker}: {e}")
        
'''
async def rapid():
    calendar_data = await process_ticker('aapl')
    print(calendar_data)
asyncio.run(rapid())''''''

'''
async def batch_main():
    tickers = await load_stocks_from_file()
    for ticker in tickers:
        await process_ticker(ticker)

if __name__ == "__main__":
    asyncio.run(batch_main())
