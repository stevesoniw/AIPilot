#Basic 함수
import time
import json
import random
import requests
import httpx
from urllib.parse import quote 
import asyncio
from io import BytesIO
from typing import List, Optional
import base64
from datetime import date, datetime, timedelta
from typing import Optional
# 기존 Util 함수들
from google.cloud import vision
from google.oauth2 import service_account
from pydantic import BaseModel
import urllib.request
from pandas import Timestamp
import pandas as pd
import numpy as np 
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from bs4 import BeautifulSoup, NavigableString
from scipy.spatial.distance import euclidean
import seaborn as sns
#금융관련 APIs
import finnhub
import fredpy as fp
from fredapi import Fred
import yfinance as yf
from openai import OpenAI
from fastdtw import fastdtw
from dtaidistance import dtw
#개인 클래스 파일 
import fredAll
#config 파일
import config
#FAST API 관련
import logging
from fastapi import FastAPI, Query, Form, HTTPException, Request, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.responses import Response

app = FastAPI()
logging.basicConfig(level=logging.DEBUG)

##############################################          공통          ################################################

# FastAPI에서 정적 파일과 템플릿을 제공하기 위한 설정
templates = Jinja2Templates(directory="chartHtml")
app.mount("/static", StaticFiles(directory="chartHtml"), name="static")

# API KEY 설정
fp.api_key =config.FRED_API_KEY
fred = Fred(api_key=config.FRED_API_KEY)
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
rapidAPI = config.RAPID_API_KEY

# 차트를 Base64 인코딩된 문자열로 변환하는 기본 함수
def get_chart_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)  # 차트 닫기
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def get_chart_base64_plotly(fig):
    # plotly figure를 이미지로 변환하고 Base64로 인코딩
    img_bytes = fig.to_image(format="png")
    return base64.b64encode(img_bytes).decode('utf-8')

##############################################          MAIN          ################################################
# 루트 경로에 대한 GET 요청 처리
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 초기 페이지 렌더링. plot_html 변수가 없으므로 비워둡니다.
    return templates.TemplateResponse("chart_pilot.html", {"request": request, "plot_html": None})

######################################## 글로벌 주요경제지표 보여주기 [1.핵심지표] Starts ###########################################
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

@app.get("/api/economic-indicators")
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
        SYSTEM_PROMPT = "You are an outstanding economist and chart data analyst. I'm going to show you annual chart data for specific economic indicators. Please explain in as much detail as possible and share your opinion on the chart trends. It would be even better if you could explain the future market outlook based on facts."
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
    
'''async def test():
    figData = await get_economic_indicators2()
    print(figData)
asyncio.run(test())'''


######################################## 글로벌 주요경제지표 보여주기 [1.핵심지표] Ends ###########################################
################################# 글로벌 주요경제지표 보여주기 [2.채권가격 차트] Starts ###########################################
# Timestamp 객체를 문자열로 변환하는 함수
def timestamp_to_str(ts):
    if isinstance(ts, Timestamp):
        return ts.strftime('%Y-%m-%d')
    return ts

# 예시 데이터 변환 함수
def convert_data_for_json(data):
    # 날짜 데이터가 들어있는 리스트를 변환
    dates_converted = [timestamp_to_str(date) for date in data.index]
    values = data.values.tolist()
    return dates_converted, values

# 기준금리 데이터를 가져오는 함수
def get_base_rate(start_date, end_date):
    df1 = fp.series('FEDFUNDS', end_date)
    data = df1.data.loc[(df1.data.index>=start_date) & (df1.data.index<=end_date)]
    return data

# 미국채 이자율 데이터를 가져와 보여주는 함수
def create_interest_rate_chart():
    rate_10Y = fred.get_series('DGS10').fillna(0)
    rate_2Y = fred.get_series('DGS2').fillna(0)
    rate_3M = fred.get_series('DGS3MO').fillna(0)

    # 현재 날짜에서 20년을 빼서 시작 날짜 계산
    twenty_years_ago = pd.to_datetime('today') - pd.DateOffset(years=20)
    
    # 데이터를 최근 20년간으로 필터링
    rate_10Y = rate_10Y[twenty_years_ago:]
    rate_2Y = rate_2Y[twenty_years_ago:]
    rate_3M = rate_3M[twenty_years_ago:]

    # Timestamp 객체를 문자열로 변환
    rate_10Y_dates = rate_10Y.index.strftime('%Y-%m-%d').tolist()
    rate_2Y_dates = rate_2Y.index.strftime('%Y-%m-%d').tolist()
    rate_3M_dates = rate_3M.index.strftime('%Y-%m-%d').tolist()

    # 차트 데이터 준비
    chart_data = [
        {'x': rate_10Y_dates, 'y': rate_10Y.values.tolist(), 'type': 'scatter', 'mode': 'lines', 'name': '10Y'},
        {'x': rate_2Y_dates, 'y': rate_2Y.values.tolist(), 'type': 'scatter', 'mode': 'lines', 'name': '2Y'},
        {'x': rate_3M_dates, 'y': rate_3M.values.tolist(), 'type': 'scatter', 'mode': 'lines', 'name': '3M'}
    ]


    # 차트 레이아웃 설정
    chart_layout = {
        'title': {
            'text': 'Market Yield on U.S. Treasury Securities',
            'font': {
                'color': 'orange',  # 제목 색상 설정
                'size': 24          # 제목 글꼴 크기 설정 (옵션)
            }
        },
        'xaxis': {'title': '날짜'},
        'yaxis': {'title': '이자율(%)'}
    }

    # JSON으로 변환 가능한 딕셔너리 반환
    return {'data': chart_data, 'layout': chart_layout}

def show_base_rate():
    # 데이터 가져오기 및 변환   #날짜 입력받는 건 나중에 하자
    start_date = '2000-01-01'
    end_date = '2023-02-01'
    data = get_base_rate(start_date, end_date)

    dates_converted, values = convert_data_for_json(data)

    # 변환된 데이터를 사용하여 차트 데이터 구성
    chart_data = [{
        'x': dates_converted,
        'y': values,
        'type': 'scatter',
        'name': '기준금리'
    }]

    chart_layout = {
        'title': {
            'text': '미국 금리 변동 추이',
            'font': {
                'color': 'black',  # 제목 색상 설정
                'size': 24          # 제목 글꼴 크기 설정 (옵션)
            }
        },        
        'xaxis': {'title': '날짜'},
        'yaxis': {'title': '금리 (%)'}
    }

    return {'data': chart_data, 'layout': chart_layout}

# 채권 차트요청 처리
@app.post("/get_bonds_data")
async def get_bonds_data():
    base_rate_chart = show_base_rate()
    interest_rate_chart = create_interest_rate_chart()

    return JSONResponse({
        "base_rate_chart": base_rate_chart,
        "interest_rate_chart": interest_rate_chart
    })

#test 
'''async def rapid():
    get_bonds_data_data = await get_bonds_data()
    print(get_bonds_data_data)
asyncio.run(rapid())'''

#### 채권 관련 뉴스 뽑아내기
def rapidapi_bond_news(category):
    url = "https://seeking-alpha.p.rapidapi.com/news/v2/list"
    querystring = {"category": category, "size": "100", "number": "1"}
    headers = {
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
    }    
        
    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

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
    return json.dumps(extracted_data, indent=4, ensure_ascii=False)

def filter_bond_news(news_json): 
    # 이 부분이 문제네..
    bond_keywords = ['bonds', 'treasury', 'FOMC', 'fixed income', 'interest rate', 'inflation', 'yield', 'credit rating', 'default risk', 'duration']
    filtered_news = {"data": []}

    for item in news_json['data']:
        title = item['attributes'].get('content', '').lower()
        if any(keyword in title for keyword in bond_keywords):
            filtered_news["data"].append(item)

    return filtered_news

# 채권관련 뉴스만 뽑아오도록 해보자 ㅠ
@app.get("/bond-news/{category}")
async def fetch_bond_news(category: str):
    news_json = rapidapi_bond_news(category)
    filtered_news_json = filter_bond_news(news_json)
    extracted_data = json.loads(extract_news_data(filtered_news_json))
    return extracted_data

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

class TranslateRequest(BaseModel):
    title: str
    content: str
@app.post("/translate")
async def translate_text(request: TranslateRequest):
    # GPT를 호출하여 번역하는 함수
    translated_title = translate_gpt(request.title)
    translated_content = translate_gpt(request.content)
    
    return {"title": translated_title, "content": translated_content}


'''테스트
async def rapid():
    get_bonds_data_data = await fetch_bond_news('market-news::top-news')
    print(get_bonds_data_data)
asyncio.run(rapid())'''


######################################## CALENDAR 보여주기 Starts ###########################################
# 증시 캘린더 관련 함수 
@app.post("/calendar", response_class=JSONResponse)
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

######################################## CALENDAR 보여주기 Ends ###########################################
######################################## NEWS 보여주기 Starts ##############################################

# Seeking Alpha 관련 뉴스 호출 함수
@app.post("/seekingNews", response_class=JSONResponse)
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

# GPT4 에 뉴스요약을 요청 
async def gpt4_news_sum(newsData, SYSTEM_PROMPT):
    try:
        prompt = "다음이 system 이 이야기한 뉴스 데이터야. system prompt가 말한대로 실행해줘. 단 답변을 꼭 한국어로 해줘. 너의 전망에 대해서는 빨간색으로 보이도록 태그를 달아서 줘. 뉴스 데이터 : " + str(newsData)
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

@app.post("/gptRequest")
async def gpt_request(request_data: dict):
    action = request_data.get("action")
    g_news = request_data.get("g_news")

    SYSTEM_PROMPT = ""
    if action == "translate":
        # 한국어로 번역하기에 대한 처리
        SYSTEM_PROMPT = "You are an expert in translation. Translate the title and content from the following JSON data into Korean. Return the translated content in the same JSON format, but only translate the title and content into Korean. Do not provide any other response besides the JSON format."
        gpt_result = await gpt4_news_sum(g_news, SYSTEM_PROMPT)

    elif action == "opinions":
        # AI 의견보기에 대한 처리
        SYSTEM_PROMPT = "Given the provided news data, please provide your expert analysis and insights on the current market trends and future prospects. Consider factors such as recent developments, market sentiment, and potential impacts on various industries based on the news. Your analysis should be comprehensive, well-informed, and forward-looking, offering valuable insights for investors and stakeholders. Thank you for your expertise"
        digest_news = extract_title_and_content(g_news)        
        gpt_result = await gpt4_news_sum(digest_news, SYSTEM_PROMPT)

    elif action == "summarize":
        # 내용 요약하기에 대한 처리
        SYSTEM_PROMPT = "You're an expert in data summarization. Given the provided JSON data, please summarize its contents systematically and comprehensively into about 20 sentences, ignoring JSON parameters unrelated to news articles."        
        digest_news = extract_title_and_content(g_news)
        gpt_result = await gpt4_news_sum(digest_news, SYSTEM_PROMPT)

    elif action == "navergpt":
        # 네이버 뉴스에 대한 GPT 의견 묻기임 
        SYSTEM_PROMPT = "You have a remarkable ability to grasp the essence of written materials and are adept at summarizing news data. Presented below is a collection of the latest news updates. Please provide a summary of this content in about 10 lines. Additionally, offer a logical and systematic analysis of the potential effects these news items could have on the financial markets or society at large, along with a perspective on future implications."        
        digest_news = g_news
        gpt_result = await gpt4_news_sum(digest_news, SYSTEM_PROMPT)        
        
    else:
        gpt_result = {"error": "Invalid action"}
    
    return {"result": gpt_result}

######################################## NEWS 보여주기 Ends  ##############################################

''' 테스트
async def gpttest():
    seekingNews_data = await rapidapi_seekingNews('market-news::top-news')
    digestNews = extract_title_and_content(seekingNews_data)
    print(digestNews)
    gpt_summary = await gpt4_news_sum(digestNews)   
    print("****************************************************************************")
    print(gpt_summary)
    
asyncio.run(gpttest()) '''
######################################## 마켓 PDF 분석 Starts  ##############################################

class ImageData(BaseModel):
    image: str  # Base64 인코딩된 이미지 데이터


@app.post("/perform_ocr")
async def perform_ocr(data: ImageData):
    # Base64 인코딩된 이미지 데이터를 디코딩
    print(data)
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


@app.post("/ocrGptTest")
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


######################################## 마켓 PDF 분석 Ends  ##############################################            
################################### FIN GPT 구현 부분 Starts (본부장님소스) ################################


def get_curday():
    return date.today().strftime("%Y-%m-%d")


def get_news (ticker, Start_date, End_date, count=20):
    news=finnhub_client.company_news(ticker, Start_date, End_date)
    if len(news) > count :
        news = random.sample(news, count)
    sum_news = ["[헤드라인]: {} \n [요약]: {} \n".format(
        n['headline'], n['summary']) for n in news]
    return sum_news 

def gen_term_stock (ticker, Start_date, End_date):
    df = yf.download(ticker, Start_date, End_date)['Close']
    term = '상승하였습니다' if df.iloc[-1] > df.iloc[0] else '하락하였습니다'
    terms = '{}부터 {}까지 {}의 주식가격은, $ {}에서 $ {}으로 {}. 관련된 뉴스는 다음과 같습니다.'.format(Start_date, End_date, ticker, int(df.iloc[0]), int(df.iloc[-1]), term)
    return terms 


# combine case1 and case2 
def get_prompt_earning (ticker):
    prompt_news_after7 = ''
    curday = get_curday()
    profile = finnhub_client.company_profile2(symbol=ticker)
    company_template = "[기업소개]:\n\n{name}은 {ipo}에 상장한 {finnhubIndustry}섹터의 기업입니다. "
    intro_company = company_template.format(**profile)    
    
    # find announce calendar 
    Start_date_calen = (datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d") # 현재 시점 - 3개월 
    End_date_calen = (datetime.strptime(curday, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")  # 현재 시점 + 1개월 
    announce_calendar= finnhub_client.earnings_calendar(_from=Start_date_calen, to=End_date_calen, symbol=ticker, international=False).get('earningsCalendar')[0]
        
    # get information from earning announcement
    date_announce= announce_calendar.get('date')
    eps_actual=announce_calendar.get('epsActual')
    eps_estimate=announce_calendar.get('epsEstimate')
    earning_y = announce_calendar.get('year')
    earning_q = announce_calendar.get('quarter')
    revenue_estimate=round(announce_calendar.get('revenueEstimate')/1000000)
       
    if eps_actual == None : # [Case2] 실적발표 전 
        # create Prompt 
        head = "{}의 {}년 {}분기 실적 발표일은 {}으로 예정되어 있습니다. 시장에서 예측하는 실적은 매출 ${}M, eps {}입니다. ".format(profile['name'], earning_y,earning_q, date_announce, revenue_estimate, eps_estimate)
        
        # [case2] 최근 3주간 데이터 수집  
        Start_date=(datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        End_date=curday
        
        # 뉴스 수집 및 추출 
        news = get_news (ticker, Start_date, End_date)
        terms_ = gen_term_stock(ticker, Start_date, End_date)
        prompt_news = "최근 3주간 {}: \n\n ".format(terms_)
        for i in news:
            prompt_news += "\n" + i 
        
        info = intro_company + '\n' + head 
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
        prompt_news = prompt_news_before + '\n' + prompt_news_after + '\n' + prompt_news_after7  
        prompt = info + '\n' +  prompt_news + '\n' + f"\n\n Based on all the information before earning call (from {Start_date_before} to {End_date_before}), let's first analyze the positive developments, potential concerns and stock price predictions for {ticker}. Come up with 5-7 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Then, based on all the information after earning call (from {date_announce} to {curday}), let's find 5-6 points that meet expectations and points that fall short of expectations when compared before the earning call. " \
        f"Finally, make your prediction of the {ticker} stock price movement for next month. Provide a summary analysis to support your prediction."    
        
        SYSTEM_PROMPT = "You are a seasoned stock market analyst working in South Korea. Your task is to list the positive developments and potential concerns for companies based on relevant news and stock price before an earning call of target companies, \
            then provide an market reaction with respect to the earning call. Finally, make analysis and prediction for the companies' stock price movement for the upcoming month. Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Market Reaction After Earning Aall]:\n[Prediction & Analysis]:\n...\n\n  Because you are working in South Korea, all responses should be done in Korean not in English. \n "

    return info, prompt_news, prompt, SYSTEM_PROMPT

def query_gpt4(ticker: str):
    # get_prompt_earning 함수로부터 4개의 값을 올바르게 받음
    info, prompt_news, prompt, SYSTEM_PROMPT = get_prompt_earning(ticker)

    # OpenAI GPT-4 호출
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    completion_content = completion.choices[0].message.content if completion.choices else "No completion found."

    # FastAPI 클라로 보내기 위해 JSON으로 변환하여 반환
    return {
        "info": info,
        "prompt_news": prompt_news,
        "completion": completion_content
    }
    
def get_historical_eps(ticker, limit=4):
    earnings = finnhub_client.company_earnings(ticker, limit)
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
    
def get_recommend_trend (ticker) : 
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


def get_one_year_before(end_date):
  end_date = datetime.strptime(end_date, "%Y-%m-%d")
  one_year_before = end_date - timedelta(days=365)
  return one_year_before.strftime("%Y-%m-%d")

def get_stock_data_daily(symbol):
  EndDate = get_curday()
  StartDate = get_one_year_before(EndDate)
  stock_data = yf.download(symbol, StartDate, EndDate)
  return stock_data[["Adj Close", "Volume"]]

def get_stock_data_fig (ticker):
    data = get_stock_data_daily(ticker)
    fig, ax1 = plt.subplots(figsize=(14, 5))
    ax1.plot(data['Adj Close'], label='Price(USD)', color='blue')
    ax1.set_xlabel('date')
    ax1.set_ylabel('Price(USD)', color='blue')
    ax1.tick_params('y', colors='blue')
    ax1.set_title(f'{ticker} Stock price and Volume Chart (recent 1 year)')
    ax2 = ax1.twinx()
    ax2.bar(data.index, data['Volume'], label='Volume', alpha=0.2, color='green')
    ax2.set_ylabel('Volume', color='green')
    ax2.tick_params('y', colors='green')
    return fig 

@app.get("/api/charts/both/{ticker}")
async def get_both_charts(ticker: str):
    # 주식 실적 이력 차트 생성 및 Base64 인코딩
    fig1 = get_historical_eps(ticker)
    earnings_chart_base64 = get_chart_base64(fig1)
    
    #print(earnings_chart_base64)
    # 애널리스트 추천 트렌드 차트 생성 및 Base64 인코딩
    fig2 = get_recommend_trend(ticker)
    recommendations_chart_base64 = get_chart_base64(fig2)

    # 두 차트의 Base64 인코딩된 이미지 데이터를 JSON으로 반환
    return JSONResponse(content={
        "earnings_chart": earnings_chart_base64,
        "recommendations_chart": recommendations_chart_base64
    })
  
@app.get("/api/analysis/{ticker}")
def get_analysis(ticker: str):
    result = query_gpt4(ticker)
    return JSONResponse(content=result)
 
@app.get("/api/stockwave/{ticker}")
def get_stockwave(ticker: str):
    fig = get_stock_data_fig(ticker)
    logging.debug(fig)
    stockwave_base64 = get_chart_base64(fig)
    return JSONResponse(content={"stockwave_data": stockwave_base64})

#################################### FIN GPT 구현 부분 Ends (본부장님소스) ###################################

''' 테스트
async def cccc():
    earnings_chart = await get_both_charts('AAPL')
    print(earnings_chart)
asyncio.run(cccc())'''

'''def queryGPT4():
    result = query_gpt4('AAPL')
    print(result)
queryGPT4()'''

############################## 국내 뉴스정보 구현 ::  네이버 검색 API + 금융메뉴 스크래핑 활용 시작 ################################

#1. 네이버 검색 API
@app.get("/api/search-naver")
async def search_naver(keyword: str = Query(default="금융")):
    client_id = config.NAVER_API_KEY
    client_secret = config.NAVER_SECRET
    encText = quote(keyword)
    naver_url = f"https://openapi.naver.com/v1/search/blog?query={encText}"

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(naver_url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Error from Naver API: {response.status_code}")

    # Process the response to match the expected format
    data = response.json()
    return {"items": data.get("items", [])}

        
#2. 네이버 증권 주요뉴스 스크래핑  :: 기본 타이틀+내용 가져오기
class NewsItem(BaseModel):
    thumb_url: Optional[str]
    article_subject: str
    article_link: Optional[str]
    summary: str
    press: str
    wdate: str
    
@app.get("/naver-scraping-news/", response_model=List[NewsItem])    
def fetch_naver_finance_news(url: str):
    try : 
        response = requests.get(url)
        # 요청이 성공적일때만
        if response.status_code == 200:
            # BeautifulSoup 객체를 생성하여 HTML을 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items  = []
            
            #메인뉴스랑 다른애들이랑 html 이 좀 다름. 분기쳐주자. 
            if 'mainnews.naver' in url: #메인뉴스 url은 현재 https://finance.naver.com/news/mainnews.naver 임                
                news_section = soup.find('div', class_='mainNewsList')
              # 각 뉴스 아이템을 순회
                for item in news_section.find_all('li', class_='block1'):
                    # Extract thumbnail image
                    thumb_element = item.select_one('.thumb img')
                    thumb_url = thumb_element['src'] if thumb_element else None
                    # Extract article subject and remark
                    # 타이틀이랑 링크까지 갖고오기 
                    article_subject_element = item.select_one('dd.articleSubject a')
                    if article_subject_element:
                        article_subject = article_subject_element.get_text(strip=True)
                        article_link = article_subject_element['href']
                    else:
                        article_subject = None
                        article_link = None
                    # Extract article summary // press랑 wdate는 포함안되게 하자
                    article_summary_element = item.select_one('dd.articleSummary')
                    if article_summary_element:
                        summary = ''.join([str(child) for child in article_summary_element.contents if type(child) == NavigableString]).strip()
                    else:
                        summary = None
                    # Extract press name
                    press = item.select_one('.press').get_text(strip=True) if item.select_one('.press') else None
                    # Extract writing date
                    wdate = item.select_one('.wdate').get_text(strip=True) if item.select_one('.wdate') else None

                    news_items.append({
                        "thumb_url": thumb_url,
                        "article_subject": article_subject,
                        "article_link": article_link,
                        "summary": summary,
                        "press": press,
                        "wdate": wdate
                    })
                return news_items                
            else: 
                news_items = []

                # 'ul class="realtimeNewsList"' 내의 모든 'li' 요소를 찾음 (각 기사 리스트)
                #  <dl> <dt><dd><dd> 순으로 1개 게시글인데 갑자기 이미지 없어져서 <dt>에 타이틀 들어올때도 있음;; 개하드코딩 필요
                for li in soup.select('ul.realtimeNewsList > li'):
                    # 'li' 내의 모든 'dl' 요소 (각 기사) 처리
                    for dl in li.find_all('dl'):
                        elements = dl.find_all(['dt', 'dd'])  # 'dt'와 'dd' 요소를 모두 찾음
                        # 초기화
                        thumb_url = None
                        article_subject = ''
                        article_link = ''
                        summary = ''
                        press = ''
                        wdate = ''
                        for element in elements:
                            if element.name == 'dt' and 'thumb' in element.get('class', []):
                                # 이미지 URL 처리
                                thumb_url = element.find('img')['src'] if element.find('img') else None
                            elif element.name == 'dt' and 'articleSubject' in element.get('class', []):
                                # 이미지 없이 제목만 있는 경우 처리
                                thumb_url = None  # 이미지가 없으므로 None으로 설정
                                article_subject = element.find('a').get('title', '')
                                article_link = "https://news.naver.com" + element.find('a')['href']
                            elif 'articleSubject' in element.get('class', []):
                                # 기사 제목 처리
                                article_subject = element.find('a').get('title', '')
                                article_link = "https://news.naver.com" + element.find('a')['href']
                            elif 'articleSummary' in element.get('class', []):
                                # 기사 요약, 출판사, 작성 날짜 처리
                                summary = element.contents[0].strip() if element.contents else ''
                                press = element.find('span', class_='press').text if element.find('span', class_='press') else ''
                                wdate = element.find('span', class_='wdate').text if element.find('span', class_='wdate') else ''
                                # 모든 정보가 수집되었으므로 news_items에 추가
                                news_items.append({
                                    "thumb_url": thumb_url,
                                    "article_subject": article_subject,
                                    "article_link": article_link,
                                    "summary": summary,
                                    "press": press,
                                    "wdate": wdate
                                })
                return news_items
        else:
            return "Failed to fetch the naverNews with status code: {}".format(response.status_code)
    except requests.exceptions.RequestException as e:
      return "An error occurred while fetching the naver news: {}".format(e)        

#왜 그런지 모르겠는데, 네이버페이지 상의 호출URL과 소스보기로 보여지는 URL이 다르다. 이거때매 url함수만듬;
def makeNaverUrl(news_url: str) :
    article_id = ""
    office_id = ""
    # '&'로 분리하여 각 파라미터를 순회
    for param in news_url.split('&'):
        # 'article_id' 파라미터인 경우
        if 'article_id=' in param:
            article_id = param.split('=')[1]
        # 'office_id' 파라미터인 경우
        elif 'office_id=' in param:
            office_id = param.split('=')[1]
    return article_id, office_id
# 문자 치환해서 뉴스 클라이언트로 보내주기
def clean_html_content(html_content: str) -> str:
    # \n을 공백으로 치환
    cleaned_content = html_content.replace('\n', ' ')
    cleaned_content = cleaned_content.replace('\t', ' ')
    cleaned_content = ' '.join(cleaned_content.split())
    return cleaned_content
# 네이버 상세 Contents 스크래핑
class NewsURL(BaseModel):
    url: str
@app.post("/api/news-detail")
def fetch_news_detail(news_url: NewsURL):
    try:
        article_id, office_id = makeNaverUrl(news_url.url)
        new_url = f"https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
        response = requests.get(new_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')            
        newsct_article = soup.find('div', id='newsct_article')
        if newsct_article is not None:
            dic_area = newsct_article.find('article', id='dic_area')
            if dic_area is not None:
                #return dic_area.prettify()  ## prettify 로 예쁘게ㅋ
                # decode_contents()로 내용을 가져온 후 개행 문자를 공백으로 치환
                html_content = dic_area.decode_contents()
                cleaned_html_content = clean_html_content(html_content)
                return cleaned_html_content
            else:
                raise HTTPException(status_code=404, detail="Article content not found")
        else:
            raise HTTPException(status_code=404, detail="News content not found")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching Naver news detail: {e}")
    
############################## 국내 뉴스정보 구현 ::  네이버 검색 API + 금융메뉴 스크래핑 활용 끝 ################################
############################## 국내 뉴스정보 구현 ::  국내 주식종목 유사국면 찾기 화면 개발 시작   ################################
#일단 종목코드 갖고오는것부터 구현하자
@app.get("/stock-codes/")    
async def stock_code_fetch():
    krxurl = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
    try:
        # 'encoding' 파라미터에 'CP949' 추가
        code_df = pd.read_html(krxurl, encoding='CP949')[0]
        code_df.종목코드 = code_df.종목코드.map('{:06d}'.format)
        code_df = code_df[['회사명', '종목코드']]
        stock_list = code_df.values.tolist()
        return stock_list
    except Exception as e:
        print(f"Stock Code 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return []
#print(stock_code_fetch())

#주식 차트 데이터 만들어서 돌려주자
class ChartRequest(BaseModel):
    stockCode: str
    fromDate: str
    toDate: str
@app.post("/stock-chart-data")
async def get_stock_chart_data(request: ChartRequest):
    try:
        ticker_symbol = request.stockCode + ".KS"
        stock = yf.Ticker(ticker_symbol)
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
    
#로컬 테스트용 함수  
async def save_to_txt(data, filename="chart_data2.txt"):
    with open(filename, "w") as file:
        json.dump(data, file)
     
'''async def rapid():
    request_data = ChartRequest(stockCode="068270", fromDate="2020-01-01", toDate="2020-12-31")
    chart_data = await get_stock_chart_data(request_data)
    await save_to_txt(chart_data, "chart_data2.txt")
asyncio.run(rapid())'''

#주식 유사국면 찾기 함수 시작. DTW 라이브러리 활용(dtaidistance씀)
class StockRequest(BaseModel):
    stockCode: str
    fromDate: str
    toDate: str
    fromDate_2: str
    toDate_2: str

@app.post("/find-similar-period")
async def find_similar_period(request: StockRequest):
    # Yahoo Finance 데이터 로드
    ticker_symbol = request.stockCode + ".KS"  # For Korean stock codes
    stock = yf.Ticker(ticker_symbol)
    
    # 전체 기간에 대한 역사적 데이터 가져오기
    hist_full = stock.history(start=request.fromDate_2, end=request.toDate_2)
    
    # 참조 기간에 대한 역사적 데이터 가져오기
    hist_ref = stock.history(start=request.fromDate, end=request.toDate)
    
    # 'Close' 가격에 초점을 맞춰 NumPy 배열로 변환
    series_ref = np.array(hist_ref['Close'], dtype=np.double)
    series_full = np.array(hist_full['Close'], dtype=np.double)
    
    # 참조 기간의 인덱스 찾기
    ref_start_idx = hist_full.index.get_loc(hist_ref.index[0])
    ref_end_idx = hist_full.index.get_loc(hist_ref.index[-1])    
   
    # 참조 기간의 길이
    len_ref = len(series_ref)    
    
    # 가장 낮은 DTW 거리와 해당 시작 인덱스 초기화
    lowest_distance = float('inf')
    best_start_index = -1    
    
    # 전체 기간 내에서 참조 기간을 제외한 부분에 대해 DTW 거리 계산
    for start_index in range(len(series_full)):
        # 참조 기간과 겹치지 않는 범위를 확인
        if start_index + len_ref - 1 < ref_start_idx or start_index > ref_end_idx:
            end_index = start_index + len_ref
            # 배열 범위 확인
            if end_index <= len(series_full):
                current_segment = series_full[start_index:end_index]
                distance = dtw.distance(series_ref, current_segment)
                
                # 가장 낮은 거리 업데이트
                if distance < lowest_distance:
                    lowest_distance = distance
                    best_start_index = start_index
                    
    # 유효한 유사 구간이 없는 경우 처리
    if best_start_index == -1:
        return {"message": "No similar period found without overlapping the reference period."}
    
                    
    # 가장 유사한 구간의 시작과 끝 날짜 찾기
    best_period_start_date = hist_full.index[best_start_index].strftime('%Y-%m-%d')
    best_period_end_date = hist_full.index[best_start_index + len_ref - 1].strftime('%Y-%m-%d')
    
    # best_start, best_end, lowest_distance 3개 값 나왔으면, 다시 야후로 해당기간 차트데이터 get ㄱㄱ
    chart_request = ChartRequest(stockCode=request.stockCode, fromDate=best_period_start_date, toDate=best_period_end_date)
    chart_data = await get_stock_chart_data(chart_request)
 
    return {"chartData": chart_data, 
            "dtwDistance": lowest_distance, 
            "bestPeriodStart": best_period_start_date, 
            "bestPeriodEnd" : best_period_end_date
            }

'''async def rapid():
    request_data = StockRequest(stockCode="068270", fromDate="2020-02-01", toDate="2020-06-30", fromDate_2="2016-01-01", toDate_2="2022-12-31" )
    wow = await find_similar_period(request_data)
    await save_to_txt(wow, "wow.txt")
asyncio.run(rapid())'''