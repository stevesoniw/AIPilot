# Util 함수들
import asyncio
import logging
from pathlib import Path
import requests
import aiofiles
import httpx
import json 
import os
from bs4 import BeautifulSoup
#금융관련 APIs
from openai import OpenAI
import finnhub
#private made 파일
import config
import utilTool

# API KEY 설정
client = OpenAI(api_key = config.OPENAI_API_KEY)
rapidAPI = config.RAPID_API_KEY
logging.basicConfig(level=logging.DEBUG)

##################################################################################################################################
#@@ 기능정의 : hot trend 해외종목 25여개에 대해서 종목뉴스를 미리 호출하고, 이들에 대한 AI의견분석을 미리 생성하는 배치 by son (24.03.31)
#@@ Logic   : 1. yahoo finance 의 most active 종목 25개 페이지를 크롤링 해와서 종목들을 list up 시킴
#@@           2. seeking alpah 종목뉴스(by RapidAPI)를 이용하여 해당 종목들의 뉴스 20개를 가져와서 json으로 저장시킴
#@@              (**파일명 :: batch/stocknews/종목코드/news_종목코드.json)               
#@@           3. 개별 종목뉴스에 대한 AI의 요약 및 의견 파일을 GPT를 활용하여 생성시킴 
#@@              (**파일명 :: batch/stocknews/종목코드/aisummary_종목코드.txt)
#@@           4. finnhub ipo calendar API를 활용하여 ipo calendar 데이터를 얻어옴
#@@         ** → 이들을 각각 파일로 저장함
#@@         ** → 최종적으로 파일들을  frCalendar.js 에서 불러와서 aiMain.html 에 넣어준다.     
#@@         ** 파일명 :: eco_calendar_eng.json, eco_calendar_kor.json, eco_calendar_aisummary.txt, ipo_calendar_eng.json
##################################################################################################################################

# 야후 인기 종목들 가져옴
async def get_active_stocks(client):
    url = 'https://finance.yahoo.com/most-active'
    try:
        response = await client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        symbols = [link.text.strip() for link in soup.select('a[data-test="quoteLink"]')]
    except Exception as e:
        print(f"웹 크롤링 중 오류 발생: {e}. 로컬 파일에서 데이터 로드 시도.")
        try:
            async with aiofiles.open('batch/hostocks.txt', 'r') as file:
                symbols = await file.read()
                symbols = symbols.splitlines()
        except Exception as e:
            print(f"파일 읽기 실패: {e}")
            symbols = []
    print(symbols)
    return symbols

# 종목뉴스 가져오기 (RapidAPI 의 seeking alpha 뉴스)
async def fetch_news(client, symbol):
    url = "https://seeking-alpha.p.rapidapi.com/news/v2/list-by-symbol"
    headers = {
        "X-RapidAPI-Key": rapidAPI,
        "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
    }
    querystring = {"id":symbol,"size":"20","number":"1"}
    response = await client.get(url, headers=headers, params=querystring)
    print(response.json())
    return response.json()

# seeking alpha 뉴스에서 쓸데없는 파라미터들 없애기
async def extract_news_data(news_json):
    extracted_data = []
    for item in news_json['data']:
        news_item = item['attributes']
        extracted_item = {
            'publishOn': news_item.get('publishOn', None),
            'gettyImageUrl': news_item.get('gettyImageUrl', None),
            'title': news_item.get('title', None),
            'content': news_item.get('content', None)
        }
        extracted_data.append(extracted_item)
    return extracted_data

# GPT4 에 뉴스요약을 요청하는 공통함수
async def gpt4_news_sum(newsData, prompt):
    try:
        SYSTEM_PROMPT = "You are an expert in analyzing news data. Please provide an in-depth summary of the following news data in 10 lines. Divide the content into title and summary, and also share your forecast on how this news will impact the future market economy and the stock price of this company"        
        completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in gpt4_news_sum function: %s", str(e))
        return None
		
# 주식 종목 코드들을 처리
async def process_stocks(symbols):
    async with httpx.AsyncClient() as client:
        for symbol in symbols:
            news_json = await fetch_news(client, symbol)
            extracted_data = await extract_news_data(news_json)
            prompt = ("The following content is news data. Execute as the system prompt instructed. "
                      "However, please make sure to respond in Korean. Attach HTML tags so that your forecast "
                      "can appear in red color. News Data : " + str(extracted_data))
            summary = await gpt4_news_sum(extracted_data, prompt)
            # 결과 저장
            directory = f'batch/stocknews/{symbol}'
            os.makedirs(directory, exist_ok=True)
            async with aiofiles.open(f'{directory}/news_{symbol}.json', 'w') as f:
                await f.write(json.dumps(extracted_data, ensure_ascii=False, indent=4))
            async with aiofiles.open(f'{directory}/aisummary_{symbol}.txt', 'w') as f:
                await f.write(summary)
                
                
async def main():
    timeout_config = httpx.Timeout(100.0)
    async with httpx.AsyncClient(timeout=timeout_config) as client:    
        symbols = await get_active_stocks(client)
        await process_stocks(symbols)

asyncio.run(main())