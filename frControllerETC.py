#Basic 함수
import json
import requests
import httpx
import os
import logging
import asyncio
from typing import Optional, List
import base64
from datetime import datetime, timedelta
# 기존 Util 함수들
from google.cloud import vision
from google.oauth2 import service_account
from pydantic import BaseModel
from urllib.parse import urlparse, parse_qs
import pandas as pd
import matplotlib
from bs4 import BeautifulSoup
matplotlib.use('Agg')
import multiprocessing
from functools import lru_cache
#금융관련 APIs
import finnhub
import fredpy as fp
from fredapi import Fred
from openai import OpenAI
import yfinance as yf
from groq import Groq
from serpapi import GoogleSearch
# import serpapi
#personal 파일
import config
import utilTool
#FAST API 관련
from fastapi import HTTPException, Request, APIRouter
from fastapi.responses import JSONResponse
#Langchain 관련
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document as Doc

# 라우터 설정
logging.basicConfig(level=logging.DEBUG)
frControllerETC = APIRouter()

# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
fp.api_key =config.FRED_API_KEY
fred = Fred(api_key=config.FRED_API_KEY)
rapidAPI = config.RAPID_API_KEY
groq_client = Groq(api_key=config.GROQ_CLOUD_API_KEY)
################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [1.핵심지표] Starts #########################################

# series id 받아서 데이터 갖고오는 공통함수 
def fetch_indicator(series_id: str, calculation: str = None) -> pd.DataFrame:
    # Fetch series data using Fred class
    df = fred.get_series(series_id=series_id)
    df = df.reset_index().rename(columns={0: 'value', 'index': 'date'})
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    if calculation == "YoY":
        df[f'{series_id}(YoY)'] = (df['value'] - df['value'].shift(12)) / df['value'].shift(12) * 100
        df = df[[f'{series_id}(YoY)']]
    return df

# 갖고 온 데이터들 합쳐서 Merge 하는 함수 
def fetch_and_merge_economic_data(start_date="2020-01-01", selected_indicators=None):
    indicators = {
        "CPIAUCSL": "YoY",
        "PCEPI": "YoY",
        "PPIFID": "YoY",
        "DFEDTARU": None,
        "CSUSHPISA": "YoY",
        "A191RL1Q225SBEA": None
    }
    
    if not selected_indicators:
        selected_indicators = ["CPIAUCSL"]  # 기본값으로 CPI 설정

    # 선택된 지표에 해당하는 데이터만 가져오기
    dfs = []
    for series_id, calculation in indicators.items():
        if series_id in selected_indicators:
            df = fetch_indicator(series_id, calculation)
            df = df.resample("D").asfreq().ffill()
            dfs.append(df)
    
    merged_df = pd.concat(dfs, axis=1).ffill()  # 여러 DataFrame을 합침
    merged_df.columns = selected_indicators  # 열 이름을 지표 ID로 설정
    return merged_df[start_date:]

#서버에서 차트 만들어서 내려주는 형태 :: 차트가 안예뻐서 일단보류;
'''@app.get("/api/economic-indicators")
async def get_economic_indicators():
    df = fetch_and_merge_economic_data("2019-01-01")
    fig = go.Figure()
    # 차트 데이터 추가
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col))
    fig.update_layout(
        title={'text': "Key Global Economic Indicators", 'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'},
        xaxis_title="Date",
        yaxis_title="Value",
    )
    economic_indicators_chart_base64 = get_chart_base64_plotly(fig)
    return JSONResponse(content={"economic_indicators_chart": economic_indicators_chart_base64}) '''

@frControllerETC.get("/api/economic-indicators")
async def get_economic_indicators(indicators: str = None, aiOpinion: Optional[bool] = False):
    if indicators:
        selected_indicators = indicators.split(",")  # 쉼표로 구분된 문자열을 리스트로 변환
    else:
        selected_indicators = ["CPIAUCSL"]  # 기본값 설정

    df = fetch_and_merge_economic_data("2020-01-01", selected_indicators)
    labels = df.index.strftime('%Y-%m-%d').tolist()
    datasets = []

    for col in df.columns:
        datasets.append({
            "label": col,
            "data": df[col].fillna(0).tolist(),
            "backgroundColor": "rgba(255, 99, 132, 0.2)",
            "borderColor": "rgba(255, 99, 132, 1)",
            "fill": False
        })

    response_data = {"labels": labels, "datasets": datasets}
    #print("labels={}".format(response_data['labels']))
    #print("datasets={}".format(response_data['datasets']))    
    if aiOpinion:
        chart_talk = await gpt4_chart_talk(response_data)
        response_data["chart_talk"] = chart_talk
    else:
        response_data["chart_talk"] = ""        
    return JSONResponse(content=response_data)

async def gpt4_chart_talk(response_data):
    try:
        SYSTEM_PROMPT = "You are an outstanding economist and chart data analyst. I'm going to show you annual chart data for specific economic indicators. Please explain in as much detail as possible and share your opinion on the chart trends. It would be even better if you could explain the future market outlook based on facts. However, Do not provide explanations or definitions for individual indicators. Instead, analyze the patterns of the data and its impact on society or the market, and share your opinion on it. Please mark the part you think is the most important with a red tag so that it appears in red."
        prompt = "다음이 system 이 이야기한 차트 데이터야. system prompt가 말한대로 분석해줘. 단 답변을 꼭 한국어로 해줘. 차트데이터 : " + str(response_data)
        completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in gpt4_news_function: %s", str(e))
        return None
##################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [1.핵심지표] Ends #########################################
##################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [2.지표분석 차트] Starts ##################################
##################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [2.지표분석 차트] Ends ##################################
##################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [2.뉴스분석 ] Starts ##################################
#### 경제지표 관련 뉴스 뽑아내기
def rapidapi_indicator_news(selected_eng_names, from_date, to_date ):
    url = "https://seeking-alpha.p.rapidapi.com/news/v2/list"
    querystring = {"category": selected_eng_names, "until": to_date, "since" : from_date, "size": "20", "number": "1"}
    headers = {
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
    }    
        
    response = requests.get(url, headers=headers, params=querystring)
    print(response.json())
    print("********************************")
    return response.json()

#print(rapidapi_bond_news('market-news::financials|market-news::issuance|market-news::us-economy'))

# seeking alpha 뉴스에서 쓸데없는 파라미터들 없애기
def extract_news_data(news_json):
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

def filter_indicator_news(news_json, selected_eng_names):
    filtered_news = {"data": []}

    for item in news_json['data']:
        title = item['attributes'].get('content', '').lower()
        if any(keyword in title for keyword in selected_eng_names):
            filtered_news["data"].append(item)

    return filtered_news

# 경제지표 관련 뉴스만 뽑아오도록 해보자 ㅠ
class DateRange(BaseModel):
    from_date: int
    to_date: int
@frControllerETC.post("/indicator-news")
async def fetch_indicator_news(date_range: DateRange):
    try:
        from_date = date_range.from_date
        to_date = date_range.to_date        
        print(from_date)
        selected_eng_names = ['market-news::financials', 'market-news::issuance', 'market-news::us-economy']
        news_json = rapidapi_indicator_news(selected_eng_names, from_date, to_date)
        #print(news_json)
        extracted_data = extract_news_data(news_json) 
        #print(extracted_data)
        return extracted_data
    except Exception as e:
        # 오류 처리
        print("Error fetching bond news:", e)
        return {"error": "Failed to fetch bond news"}

# 채권뉴스 GPT 이용해서 번역해보기 //메뉴3 일반뉴스 번역에서도 씀
def translate_gpt(text):
    try:
        SYSTEM_PROMPT = "다음 내용을 한국어로 번역해줘. url이나 링크 부분만 번역하지마" 
        prompt = f"영어를 한국어로 번역해서 알려줘. 내용은 다음과 같아\n{text}"
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in translate_gpt function: %s", str(e))
        return None       

def translate_lama(text):
    try:
        SYSTEM_PROMPT = "다음 내용을 한국어로 번역해줘. url이나 링크 부분만 번역하지마" 
        prompt = f"영어를 반드시 한국어로 번역해서 알려줘. url과 링크를 제외한 답변내용은 반드시 한국어여야해. 내용은 다음과 같아\n{text}"
        response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in translate_lama function: %s", str(e))
        return None    

class FrNewsTranslateRequest(BaseModel):
    title: str
    content: str
    method: str  # Method to decide the translation function (e.g., "lama" or "gpt")
@frControllerETC.post("/frnews-translate")
async def translate_text(request: FrNewsTranslateRequest):
    if request.method.lower() == "lama":
        translate_func = translate_lama
    else:
        translate_func = translate_gpt

    translated_title = translate_func(request.title)
    translated_content = translate_func(request.content)
    
    return {"title": translated_title, "content": translated_content}

class TranslateRequest(BaseModel):
    title: str
    content: str
@frControllerETC.post("/translate")
async def translate_text(request: TranslateRequest):
    # GPT를 호출하여 번역하는 함수
    translated_title = translate_gpt(request.title)
    translated_content = translate_gpt(request.content)
    
    return {"title": translated_title, "content": translated_content}
##################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [2.채권가격 차트] Ends ##################################
##################################[1ST_GNB][5TH_MENU] CALENDAR 보여주기 Starts #####################################################
# 증시 캘린더 관련 함수 
@frControllerETC.post("/calendar", response_class=JSONResponse)
async def get_calendar(request: Request):
    calendar_data = await rapidapi_calendar()
    return JSONResponse(content=calendar_data)  # JSON 형식으로 데이터 반환

                        
async def rapidapi_calendar():
    url = "https://trader-calendar.p.rapidapi.com/api/calendar"
    payload = { "country": "USA", "start":"2023-12-01"}
    headers = {
	    "content-type": "application/json",
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "trader-calendar.p.rapidapi.com"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
    calendar_data = response.json()
    return calendar_data

@frControllerETC.post("/calendar/ipo", response_class=JSONResponse)
async def get_ipo_calendar():
    try:
        #현재 날짜를 기준으로 Finnhub에서 데이터 조회 (일단 데이터없는 종목들이 많아서 3개월치 가져온다)
        Start_date_calen = (datetime.strptime(utilTool.get_curday(), "%Y-%m-%d") - timedelta(days=180)).strftime("%Y-%m-%d") # 현재 시점 - 6개월 
        End_date_calen = (datetime.strptime(utilTool.get_curday(), "%Y-%m-%d") + timedelta(days=90)).strftime("%Y-%m-%d")   
        recent_ipos = finnhub_client.ipo_calendar(_from=Start_date_calen, to=End_date_calen)
        return JSONResponse(content=recent_ipos) 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#다우 차트 데이터 만들어서 돌려주자
class CalendarChartRequest(BaseModel):
    fromDate: str
    toDate: str
@frControllerETC.post("/calendar-us-chart")
async def get_calendar_dowchart_data(request: CalendarChartRequest):
    try:
        stock = yf.Ticker("^DJI")
        hist = stock.history(start=request.fromDate, end=request.toDate)
        # pandas DataFrame의 인덱스(날짜)를 'Date' 컬럼으로 변환
        hist.reset_index(inplace=True)
        # 'Date' 컬럼을 확인하고 필요한 경우 datetime 타입으로 변환
        if not pd.api.types.is_datetime64_any_dtype(hist['Date']):
            hist['Date'] = pd.to_datetime(hist['Date'])
        # 'Date' 컬럼을 문자열로 변환
        hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
        # 차트 데이터 구성
        chart_data = {
            'labels': hist['Date'].tolist(),
            'datasets': [
                {'label': 'Open', 'data': hist['Open'].tolist()},
                {'label': 'High', 'data': hist['High'].tolist()},
                {'label': 'Low', 'data': hist['Low'].tolist()},
                {'label': 'Close', 'data': hist['Close'].tolist()},
            ]
        }
        #await save_to_txt(chart_data, "chart_data2.txt")
        return {"chartData": chart_data}
    except Exception as e:
        print(f"Error fetching stock chart data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching stock chart data")    
    
#print(get_ipo_calendar())
##################################[1ST_GNB][6TH_MENU] CALENDAR 보여주기 ENDS #####################################################
##################################[1ST_GNB][3RD_MENU] 해외 증시 NEWS 보여주기 Starts ###################################################

# Seeking Alpha 관련 뉴스 호출 함수
@frControllerETC.post("/seekingNews", response_class=JSONResponse)
async def get_seekingNews(request: Request):
    form_data = await request.json()
    categories = form_data.get("categories", [])
    category_query = "|".join(categories)
    original_seekingNews = await rapidapi_seekingNews(category_query)
    seekingNews_data = extract_news_data(original_seekingNews)
    return JSONResponse(content=seekingNews_data)   
    
async def rapidapi_seekingNews(categories):
    url = "https://seeking-alpha.p.rapidapi.com/news/v2/list"
    querystring = {"category": categories, "size": "10", "number": "1"}
    #querystring  = {"category":"market-news::top-news|market-news::on-the-move|market-news::market-pulse|market-news::notable-calls|market-news::buybacks","size":"50","number":"1"}
    headers = {
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
    }
    
    response = requests.get(url, headers=headers, params=querystring)
    return response.json() 

'''# RapidAPI 테스트용
async def rapid():
    calendar_data = await rapidapi_calendar()
    print(calendar_data)
asyncio.run(rapid())'''

'''# Fred Data 테스트용
def fred_test():
    #data = fred.search_by_release(release_id=1, limit=0, order_by=None, filter="bonds")
    data2 = fred.get_data(api_name="series_search", search_text="FOMC")
    print(data2)
fred_test()'''

# 뉴스 json에서 gpt로 던질 내용만 뽑아내기
def extract_title_and_content(json_str):
    json_data = json.loads(json_str)
    title_and_content = []
    for item in json_data:
        title = item['title']
        content = item['content']
        title_and_content.append({'title': title, 'content': content})
    return title_and_content

@frControllerETC.post("/gptRequest")
async def gpt_request(request_data: dict):
    action = request_data.get("action")
    g_news = request_data.get("g_news")
    llm = request_data.get("llm", None)
    if llm == 'lama':
        #news_sum_function = utilTool.lama3_news_sum
        news_sum_function = utilTool.mixtral_news_sum        
    else:
        news_sum_function = utilTool.gpt4_news_sum    

    SYSTEM_PROMPT = ""
    if action == "translate":
        # 한국어로 번역하기에 대한 처리
        SYSTEM_PROMPT = "You are an expert in translation. Translate the title and content from the following JSON data into Korean. Return the translated content in the same JSON format, but only translate the title and content into Korean. Do not provide any other response besides the JSON format."
        gpt_result = await news_sum_function(g_news, SYSTEM_PROMPT)

    elif action == "opinions":
        # AI 의견보기에 대한 처리
        SYSTEM_PROMPT = "Given the provided news data, please provide your expert analysis and insights on the current market trends and future prospects. Consider factors such as recent developments, market sentiment, and potential impacts on various industries based on the news. Your analysis should be comprehensive, well-informed, and forward-looking, offering valuable insights for investors and stakeholders. Thank you for your expertise"
        #digest_news = extract_title_and_content(g_news)        
        gpt_result = await news_sum_function(g_news, SYSTEM_PROMPT)

    elif action == "summarize":
        # 내용 요약하기에 대한 처리
        SYSTEM_PROMPT = "You're an expert in data summarization. Given the provided JSON data, please summarize its contents systematically and comprehensively into about 20 sentences, ignoring JSON parameters unrelated to news articles."        
        #digest_news = extract_title_and_content(g_news)
        gpt_result = await news_sum_function(g_news, SYSTEM_PROMPT)

    elif action == "navergpt":
        # 네이버 뉴스에 대한 GPT 의견 묻기임 
        SYSTEM_PROMPT = "You have a remarkable ability to grasp the essence of written materials and are adept at summarizing news data. Presented below is a collection of the latest news updates. Please provide a summary of this content in about 10 lines. Additionally, offer a logical and systematic analysis of the potential effects these news items could have on the financial markets or society at large, along with a perspective on future implications."        
        digest_news = g_news
        gpt_result = await news_sum_function(digest_news, SYSTEM_PROMPT)        
        
    else:
        gpt_result = {"error": "Invalid action"}
    
    return {"result": gpt_result}

##################################[1ST_GNB][3RD_MENU] 해외 증시 NEWS 보여주기 ENDS ###################################################

''' 테스트
async def gpttest():
    seekingNews_data = await rapidapi_seekingNews('market-news::top-news')
    digestNews = extract_title_and_content(seekingNews_data)
    print(digestNews)
    gpt_summary = await gpt4_news_sum(digestNews)   
    print("****************************************************************************")
    print(gpt_summary)
    
asyncio.run(gpttest()) '''
#####################################[TEST 없어진 MENU] 해외 증시 마켓 PDF 분석 Starts ################################################

class ImageData(BaseModel):
    image: str  # Base64 인코딩된 이미지 데이터

@frControllerETC.post("/perform_ocr")
async def perform_ocr(data: ImageData):
    # Base64 인코딩된 이미지 데이터를 디코딩
    image_data = base64.b64decode(data.image.split(',')[1])

    logging.debug(image_data)

    # 서비스 계정 키 파일 경로
    key_path = "sonvision-36a28cdac666.json"

    # 서비스 계정 키 파일을 사용하여 인증 정보 생성
    credentials = service_account.Credentials.from_service_account_file(key_path)

    # 인증 정보를 사용하여 Google Cloud Vision 클라이언트 초기화
    client = vision.ImageAnnotatorClient(credentials=credentials)

    image = vision.Image(content=image_data)

    # OCR 처리
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if response.error.message:
        raise HTTPException(status_code=500, detail=response.error.message)

    # OCR 결과 반환
    return {"texts": [text.description for text in texts]}

def process_ocr_texts(texts):
    processed_texts = []
    for text in texts:
        description = text.description
        processed_texts.append(description)
    
    return processed_texts

@frControllerETC.post("/ocrGptTest")
async def perform_ocr(data: ImageData):
    # Base64 인코딩된 이미지 데이터를 디코딩
    image_data = base64.b64decode(data.image.split(',')[1])
    # 서비스 계정 키 파일 경로
    key_path = "sonvision-36a28cdac666.json"

    # 서비스 계정 키 파일을 사용하여 인증 정보 생성
    credentials = service_account.Credentials.from_service_account_file(key_path)
    # 인증 정보를 사용하여 Google Cloud Vision 클라이언트 초기화
    client = vision.ImageAnnotatorClient(credentials=credentials)
    image = vision.Image(content=image_data)
    # OCR 처리
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if response.error.message:
        raise HTTPException(status_code=500, detail=response.error.message)

    structured_ocr_data = process_ocr_texts(texts)
    # OCR 결과를 GPT-4 분석 함수에 전달
    analysis_result = await gpt4_pdf_talk(structured_ocr_data)

    # 분석 결과 반환
    return {"texts": analysis_result}

async def gpt4_pdf_talk(response_data):
    try:
        SYSTEM_PROMPT = "You are a financial data analyst with outstanding data recognition skills. The following is table data on market data interest rates and exchange rates. This data is not structured because it was read using OCR. However, knowing that this is data read from a table using OCR, please explain this data systematically. Provide as detailed and accurate a response as possible."
        prompt = f"The following is OCR extracted table data. Analyze it as the system prompt has described. The response should be in Korean. Extracted data: {response_data}"
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("An error occurred in gpt4_chart_talk:", str(e))
        return None
##################################[TEST 없어진 메뉴] 해외 증시 마켓 PDF 분석 ENDS ################################################### 
################################### [1ST GNB][4TH LNB] FOMC 데이터 분석 Starts############################################

#############(1. FOMC PRESS Release 분석 )

# FOMC 데이터 스크래핑 [1차 press relase 타이틀목록 조회용] 
@frControllerETC.get("/fomc-scraping-release/")    
def fetch_fomc_press_release(url: str):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # UTF-8 BOM이 있을 경우를 대비하여 utf-8-sig로 디코드
            data = response.content.decode('utf-8-sig')
            json_data = json.loads(data)[:10]  
            data_list = []
            for item in json_data:
                datetime = item.get("d")
                title = item.get("t")
                press_type = item.get("pt")
                link = "https://www.federalreserve.gov" + item.get("l") 
                
                data_list.append({
                    'datetime': datetime,
                    'title': title,
                    'link': link,
                    'press_type': press_type
                })
            return data_list
        else:
            return "Failed to fetch FOMC title data with status code: {}".format(response.status_code)
    except Exception as e:  
        raise HTTPException(status_code=400, detail=str(e))    

#print(fetch_fomc_press_release('https://www.federalreserve.gov/json/ne-press.json'))
# FOMC 데이터 스크래핑 [1차 press relase 상세내용 조회용] 
@frControllerETC.get("/fomc-scraping-details-release/")    
async def fetch_fomc_press_release(url: str):
    try:
        response = requests.get(url)
        # URL 예시 :: https://www.federalreserve.gov/newsevents/pressreleases/bcreg20240424a.htm
        if response.status_code == 200:
            # UTF-8 BOM이 있을 경우를 대비하여 utf-8-sig로 디코드
            data = response.content.decode('utf-8-sig')
            
            soup = BeautifulSoup(data, 'html.parser')
            # 타이틀을 뽑고
            title = soup.find('h3', class_='title').text.strip()
            # 콘텐츠를 뽑고
            contents = soup.find('div', id='article').find_all('p')
            contents_text = '\n'.join(p.text for p in contents if 'article__time' not in p.get('class', []))
            # join해서 gpt로 던지자 
            data_list = f"Title: {title}\nContents:\n{contents_text}"

            SYSTEM_PROMPT = "너는 뉴스데이터 분석전문가야. 다음 뉴스 데이터를 7줄로 심도있게 요약해줘. 타이틀과 요약으로 나누어서 내용을 보여주고 이 뉴스가 향후 시장경제에 미치게 될 너의 전망도 같이 알려줘"
            summary = await utilTool.gpt4_news_sum(data_list, SYSTEM_PROMPT)
            
            ##### 파일 저장도 따로 한다!! (속도개선) #####
                        # 파일 이름 추출
            filename = url.split('/')[-1].split('.')[0] + '.txt'
            save_path = f"batch/fomc/fomc_detail_{filename}"
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as file:
                file.write(summary)
            
            return summary            
        else:
            return f"Failed to fetch FOMC release detail data with status code: {response.status_code}"
    except Exception as e:  
        raise HTTPException(status_code=400, detail=str(e))
    
#############(2.FOMC 위원들 Speech 요약 및  분석 )

def scrape_speeches(url):
    """
    URL 입력했을 때 최근 FOMC 스피치 리스트를 가져오는 함수
    """
    try: 
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
   
        # Find the parent div with class 'row eventlist'
        eventlist_div = soup.find('div', class_='row eventlist')

        # Find the desired section within the parent div
        desired_section = eventlist_div.find('div', class_='col-xs-12 col-sm-8 col-md-8')

        speeches = []

        for speech in desired_section.find_all('div', class_='row'):
            # print(speech)
            # print("*****")
            date = speech.find('time').text
            link = 'https://www.federalreserve.gov' + speech.find('div', class_='col-xs-9 col-md-10 eventlist__event').find('a', href=True)['href']
            title = speech.find('em').text
            author = speech.find('p', class_='news__speaker').text
            # youtube = speech.find('a', class_='watchLive')
            # if youtube:
            #     youtube_link = speech.find('a', class_='watchLive')['href']
            #     speeches.append({'date': date, 'link': link, 'title': title, 'author': author, 'youtube_link': youtube_link})
            # else: # youtube link doesn't exist
            speeches.append({'date': date, 'link': link, 'title': title, 'author': author})

        return speeches
    except requests.exceptions.RequestException as e:
        return "An error occurred while fetching speech news: {}".format(e)  
    
def scrape_speech_content(url):
    """
    URL 입력했을 때 URL 안에 있는 스피치 텍스트를 가져오는 함수
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    desired_section = soup.find('div', class_='col-xs-12 col-sm-8 col-md-8')
    
    ### 비디오 내용 제거
    unwanted_div = desired_section.find('div', class_='col-xs-12 col-md-7 pull-right')
    if unwanted_div:
        unwanted_div.decompose()
    ## 엔딩을 가리키는 hr태그 찾기
    hr_tag = desired_section.find('hr')
    # Extract the content before the <hr> tag
    if hr_tag:
        previous_content = hr_tag.find_previous_siblings()
        result_str = ""
        for tag in reversed(previous_content):
            # print(tag)
            result_str += tag.text + "\n\n"
    else:
        result_str = desired_section.text.strip()
    
    return result_str    

@frControllerETC.get("/frSocialData")
async def get_fr_social_data(request: Request):
    scraped_data_2024 = scrape_speeches("https://www.federalreserve.gov/newsevents/speech/2024-speeches.htm")
    scraped_data_2023 = scrape_speeches("https://www.federalreserve.gov/newsevents/speech/2023-speeches.htm")
    scraped_data = scraped_data_2024 + scraped_data_2023
    
    
    logging.info("======GETTING SOCIAL DATA =======")
    return {"data": scraped_data}

class SpeechData(BaseModel):
    title: str
    link: str
    

@lru_cache(maxsize=None)  # 요약이 너무 오래 걸려서 한번 나온 결과는 캐싱한다
def generate_content(text):
    # Your function logic here
    prompt_template = """You are an economist tasked with summarizing speeches by Federal Open Market Committee (FOMC) members.
    Explain as if you are talking to someone who knows nothing about FOMC or economics. So, you have to explain economics terminology used in the text as well.
    너한테 FOMC 연설문 전체 내용을 줄 거야. 연설문의 주요 내용을 요약해줘. 고유명사는 괄호로 영어 원문도 보여줘.
    대답은 한국어로 해줘. 답변은 500자 이내로 해줘. Speech에 없는 내용은 언급하지 마.
    연설자를 가리킬 때는 항상 "연설자" 라고 말해. 다른 명칭을 사용하지 마. 
    답은 항상 -입니다, -습니다 체로 해줘. 
    
    Speech:
    "{text}"

    답변: """

    prompt = PromptTemplate.from_template(prompt_template)

    # Define LLM chain
    llm = ChatOpenAI(temperature=0.1, model_name="gpt-4-turbo", api_key=config.OPENAI_API_KEY, 
                     streaming=True)
    llm_chain = LLMChain(llm=llm, prompt=prompt)

    # Define StuffDocumentsChain
    stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="text", verbose=True)
    docs = Doc(page_content=text)
    return stuff_chain.run([docs])


@frControllerETC.post("/summarizeSpeech")
async def summarize_speech(data: SpeechData):
    try:    
        #파일 저장용 이름따내기
        parsed_url = urlparse(data.link)
        file_name_with_extension = os.path.basename(parsed_url.path)   
        file_id = file_name_with_extension.split('.')[0]   
        
        speech_title = translate_gpt(data.title)  #타이틀 번역하기
        speech_text = scrape_speech_content(data.link) # 링크 가서 내용 크롤링하기
        summary = generate_content(speech_text)    
            
        result = {"title": speech_title, "summary": summary}
        
        #retrun 할 데이터를 파일로도 저장시킴(for 속도개선)
        file_path = f"batch/fomc/fomc_speech_ai_sum_{file_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False)  
        return result    
    except Exception as e:
        print(f"Error saving file(at summarize_speech): {e}")
        #파일저장에서 에러나도 어쨌든 리턴은 되게..
        return result
    
    
#############(3.FOMC 위원들 성향분석 )###############

#### 사람별로 관련 로이터 article 가져오는 함수 (serp api 활용)
def get_articles_by_person(person):
    """
    사람 이름 (ex. John Williams) 입력했을 때 구글서치로 뜨는 로이터 기사들 가져오는 함수
    """
    params = {
        #   "engine": "google_news",
        "tbm": "nws",
        "q": f"{person} Reuters",
        "api_key": config.SERPAPI_API_KEY,
        #   "tbs": "sbd:1", ##sort by date
        "num": 20        
    }

    try:
        # search = GoogleSearch(params)
        # search_result  = serpapi.search(params)
        search = GoogleSearch(params)
        results = search.get_dict()
        print(results)
        news_results = results["news_results"]
        # print(news_results)
        
        # 출처가 로이터 인것만 필터링
        reuters_articles = [article for article in news_results if article['source'] == 'Reuters']
        
        # 타이틀에 사람 이름이 들어간 것만 필터링
        filtered_articles = [article for article in reuters_articles if person.split()[-1].lower() in article['title'].lower()]
        
        # 날짜 중복인 것들 중에 중복 제거
        encountered_dates = set()
        final_articles = []
        
        for article in filtered_articles:
            formatted_date = utilTool.parse_date(article['date'])    #상대적인 날짜 있는 경우 절대날짜로 변환해주기
            if formatted_date and formatted_date not in encountered_dates:
                article['date'] = formatted_date
                final_articles.append(article)
                encountered_dates.add(formatted_date)
                
        return final_articles
    except Exception as e: 
        raise HTTPException(status_code=400, detail=str(e))
        

class ArticleRequest(BaseModel):
    name: str
@frControllerETC.post("/articleData")
async def get_article_data(request: ArticleRequest):
    return get_articles_by_person(request.name)



class SentimentAnalysisRequest(BaseModel):
    speeches: List

@lru_cache(maxsize=None)    
def extract_main_sentence(url):
    """
    url에 대해 url 텍스트 전체를 크롤링하고 텍스트 중 주요 문장 추출하는 함수
    """
    text = scrape_speech_content(url)
    prompt_template = """
    You are an economist determining dovish/hawkish orientation from FOMC members' speeches.
    You will be given a speech from a FOMC member. 
    Return the main sentence from the speech that shows author's orientation. 
    If the speech does not contain such sentence, return None.
    
    The output should just be the sentence(s). Do not include other explanations.
        <Example>
        "There is no rush in cutting interest rates."

    Speech:
    "{text}"

    Answer: """
    prompt = PromptTemplate.from_template(prompt_template)

    # Define LLM chain
    llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo", streaming=True,
                     api_key=config.OPENAI_API_KEY)
    llm_chain = LLMChain(llm=llm, prompt=prompt)

    # Define StuffDocumentsChain
    stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="text", verbose=True)
        
    docs = Doc(page_content=text)
    # #     # # result1 = stuff_chain.invoke(docs)['output_text']
    # #     # # print(stuff_chain.invoke(docs))
    # #     # # # print(stuff_chain.run(docs))
    # #     # # print(type(docs))
    return stuff_chain.run([docs])



@frControllerETC.post("/sentimentAnalysis")
async def get_sentiment_data(request: SentimentAnalysisRequest):
    speeches = request.speeches
    if len(speeches) > 15:
        speeches = speeches[0:15] # 15개로 제한

    with multiprocessing.Pool(processes=10) as pool:
        # 주요 문장 뽑기 병렬 처리
        results = [pool.apply_async(extract_main_sentence, (speech["link"],)) for speech in speeches]

        final_results = []
        for speech, result in zip(speeches, results):
            extracted_result = result.get()  # 결과 받기
            if extracted_result is None or extracted_result == "None":  # 결과가 None인 경우 간지나게 바꿈
                extracted_result = "No significant remarks were made."
            final_results.append({"date": speech["date"], "title": speech["title"], "result": extracted_result})

        print("Final Results:", final_results)

    return final_results


### FOMC Sentiment Analysis 모델에 텍스트 보내고 스코어 받아오는 함수
def query(payload):
    """
    fomc-roberta 모델에 내가 원하는 문장을 보내서 문장에 대한 성향분석 점수를 받아오는 함수
    """
    API_URL = "https://api-inference.huggingface.co/models/gtfintechlab/FOMC-RoBERTa"
    headers = {"Authorization": f"Bearer {config.HUGGINGFACE_API_KEY}"}
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()
	
        
class SentimentScoreRequest(BaseModel):
    speeches: List
    is_speech: bool
    
@frControllerETC.post("/sentimentScore")
async def get_sentiment_data(request: SentimentScoreRequest):
    speeches = request.speeches
    final_results = []
    for speech in speeches:
        if request.is_speech == True: # 연설문 주요문장에서 점수 추출
            if speech["result"] != "None": 
                output = query({
                    "inputs": speech["result"],
                    "options": {
                        "wait_for_model": True
                    }
                })
                final_results.append({"date": speech["date"], "scores": output, "result": speech["result"]})    
            else:
                continue
        else: # 기사 제목에서 점수 추출
            output = query({
                "inputs": speech["title"],
                "options": {
                    "wait_for_model": True
                    }
                })
            final_results.append({"date": speech["date"], "scores": output, "result": speech["title"]})    
        
    logging.info(final_results)
    return final_results

################################### [1ST GNB][4TH LNB] FOMC 데이터 분석 Ends############################################        