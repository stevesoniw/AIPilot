# Util 함수들
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
import requests
import aiofiles
import aiohttp
import httpx
import json 
import os
from bs4 import BeautifulSoup
#금융관련 APIs
from openai import OpenAI
import finnhub
from groq import Groq
#private made 파일
import config
import utilTool
#langchain 관련
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders.web_base import WebBaseLoader
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import LLMChain

# API KEY 설정
client = OpenAI(api_key = config.OPENAI_API_KEY)
rapidAPI = config.RAPID_API_KEY
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
groq_client = Groq(api_key=config.GROQ_CLOUD_API_KEY)
logging.basicConfig(level=logging.DEBUG)

##################################################################################################################################
#@@ 기능정의 : hot trend 해외종목 25여개에 대해서 종목뉴스를 미리 호출하고, 이들에 대한 AI의견분석을 미리 생성하는 배치 by son (24.03.31)
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

        async with aiofiles.open('batch/hotstocks.txt', 'w') as file:
            await file.write('\n'.join(symbols))
        print("Stocks data saved successfully.")
        return True
    except Exception as e:
        print(f"웹 크롤링 중 오류 발생: {e}")
        return False
    
# 혹시 수동으로 종목을 입력해서 가져와야될 경우도 있을것 같아, 파일로 먼저 저장하고, 이후 읽어오는 2단계로 변경함. 
# 귀찮으니 수동으로 기입하는 파일도 따로 만들자. 
async def load_stocks_from_file():
    try:
        # 두 파일의 경로를 리스트로 관리
        files = ['batch/hotstocks_manual.txt', 'batch/hotstocks.txt']
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

        

# 종목뉴스 가져오기 (RapidAPI 의 seeking alpha 뉴스)
async def fetch_news_seekingalpha(client, symbol):
    url = "https://seeking-alpha.p.rapidapi.com/news/v2/list-by-symbol"
    headers = {
        "X-RapidAPI-Key": rapidAPI,
        "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
    }
    querystring = {"id":symbol,"size":"20","number":"1"}
    try:
        response = await client.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # 이 부분은 HTTP 요청이 실패했을 때 예외를 발생시킵니다.
        news_json = response.json()
        if 'data' in news_json and len(news_json['data']) > 0:
            return news_json
        else:
            print(f"No news data found for symbol: {symbol}")
            return None  # 뉴스 데이터가 없을 경우 None 반환
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred while fetching news for {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return None

# seeking alpha 뉴스에서 쓸데없는 파라미터들 없애기
async def extract_news_data(news_json):
    extracted_data = []
    for item in news_json['data']:
        news_item = item['attributes']
        extracted_item = {
            'publishOn': news_item.get('publishOn', None),
            #'gettyImageUrl': news_item.get('gettyImageUrl', None),
            'title': news_item.get('title', None),
            #'content': news_item.get('content', None)
        }
        extracted_data.append(extracted_item)
    return extracted_data

# Finnhub 종목뉴스도 가져오자. 
async def fetch_news_finnhub(symbol):
    try:
        # 현재 날짜를 기준으로 Finnhub에서 데이터 조회 (일단 3개월치 데이터.)
        start_date_calen = (datetime.strptime(utilTool.get_curday(), "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
        end_date_calen = utilTool.get_curday()     
        recent_news = finnhub_client.company_news(symbol, _from=start_date_calen, to=end_date_calen)
        # 최근 15개의 뉴스만 반환하자.
        if len(recent_news) > 15:
            return recent_news[:15]
        else:
            return recent_news
    except Exception as e:
        print(f"Finnhub 뉴스를 가져오는 데 실패했습니다: {e}")
        
async def save_summary_to_file(directory, symbol, news_id, summary):
    filename = f"{symbol}_{news_id}.txt"
    filepath = os.path.join(directory, filename)
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(summary['text'])  

# GPT4 에 뉴스요약을 요청하는 공통함수
async def gpt4_news_sum(prompt):
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

# Lama3 API 로 TEST 해보기
async def lama3_news_sum(prompt):
    try:
        SYSTEM_PROMPT = "You are an expert in analyzing news data. Please provide an in-depth summary of the following news data in 10 lines. Divide the content into title and summary, and also share your forecast on how this news will impact the future market economy and the stock price of this company. make sure to answer in Korean"     
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
  
# 주식 메인뉴스를 생성하고, ai summary와 기본뉴스를 json으로 저장
async def process_stock_main_news(symbols):
    async with httpx.AsyncClient() as client:
        for symbol in symbols:
            news_json = await fetch_news_seekingalpha(client, symbol)
            if news_json:  # 뉴스 데이터가 있을 때만 처리
                extracted_seekingalpha = await extract_news_data(news_json)
                extracted_finnhub = await fetch_news_finnhub(symbol)
                prompt = ("The following content is news data. Execute as the system prompt instructed. "
                          "Please make sure to respond in Korean. Attach HTML tags so that your forecast "
                          "can appear in '#ff1480' color. Your response will be displayed on an HTML screen. Therefore, include many appropriate <br> tags and other useful tags to make it easy for people to read."
                          "News Data : " + str(extracted_seekingalpha) + str(extracted_finnhub))
                summary = await gpt4_news_sum(prompt)
                # 결과 저장
                directory = f'batch/stocknews/{symbol}'
                os.makedirs(directory, exist_ok=True)
                todayDate = datetime.now().strftime("%Y%m%d")
                async with aiofiles.open(f'{directory}/news_{symbol}_{todayDate}.json', 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(extracted_finnhub, ensure_ascii=False, indent=4))
                async with aiofiles.open(f'{directory}/aisummary_{symbol}_{todayDate}.txt', 'w', encoding='utf-8') as f:
                    await f.write(summary)
            else:
                print(f"Skipping processing for {symbol} due to lack of news data.")    
                
async def process_stock_detail_news(symbols):
    async with aiohttp.ClientSession() as session:
        for symbol in symbols:
            directory = f'batch/stocknews/{symbol}'
            os.makedirs(directory, exist_ok=True)
            try:
                async with aiofiles.open(f'{directory}/news_{symbol}.json', 'r', encoding='utf-8', errors='ignore') as f:
                    data = await f.read()
                    news_data = json.loads(data)
            except FileNotFoundError:
                print(f"File not found for symbol: {symbol}")
                continue
            
            #for news_item in news_data:
            for news_item in news_data[:2]:  #처음 두개만 하자 일단.. 속도땜시
                news_id = news_item['id']
                news_url = news_item['url']
                # 각 뉴스 항목에 대한 요약 메시지 받아오기
                summary = await webNewsAnalyzer(news_url)
                print("*********************************")
                print(summary)
                print("*********************************")
                # 요약 메시지를 파일에 저장
                await save_summary_to_file(directory, symbol, news_id, summary)                        
                
async def webNewsAnalyzer(url):
    text_splitter = CharacterTextSplitter(chunk_size=1024, chunk_overlap=100, length_function=len, separator= "\n\n\n")    
    docs = WebBaseLoader(url).load_and_split(text_splitter) #BSHTMLLoader 가 WebBaseLoader 보다 더 가벼운듯함. 컴팩트하게 긁어옴
    LLM_MODEL_NAME = "gpt-4-0125-preview"
    combine_template = '''{text}
    위 내용을 반드시 한국어로 요약해줘
    Your response will be displayed on an HTML screen. Therefore, include appropriate <br> tags and other useful tags to make it easy for people to read.
    요약의 결과는 다음의 형식으로 작성해줘. 깔끔하게 줄바꿈되어 보일수있게 반드시 html형식으로 답변해줘. 그리고 한국어로 답변해줘 :
    [답변 형식]
    제목: 신문기사의 제목
    주요내용: 여섯 줄로 요약된 내용
    내용: 주요내용을 불렛포인트 형식으로 작성
    AI의견 : 해당 뉴스가 관련 주식 종목에 미칠만한 영향과 향후 주시해야 하는 포인트 
    '''
    prompt = PromptTemplate(template=combine_template, input_variables=['text'])
    #combine_prompt = PromptTemplate(template=combine_template, input_variables=['text'])
    
    llm = ChatOpenAI(temperature=0, model=LLM_MODEL_NAME, openai_api_key=config.OPENAI_API_KEY)
    chain = LLMChain(
                    prompt=prompt, 
                    #combine_prompt=combine_prompt, 
                    llm=llm)
    result = chain.invoke(docs)
    return result                


               
async def main():
    timeout_config = httpx.Timeout(10000.0)
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        # 메인 뉴스 처리
        await handle_main_news(client)

async def handle_main_news(client):
    success = await scrape_and_save_stocks(client)
    symbols = await load_stocks_from_file()
    await process_stock_main_news(symbols)
    await process_stock_detail_news(symbols)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

#print(fetch_news_finnhub('AAPL'))