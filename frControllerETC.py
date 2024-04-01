#Basic 함수
import json
import requests
import httpx
import asyncio
from typing import Optional
import base64
from datetime import datetime, timedelta
from typing import Optional
# 기존 Util 함수들
from google.cloud import vision
from google.oauth2 import service_account
from pydantic import BaseModel
import pandas as pd
import matplotlib
matplotlib.use('Agg')
#금융관련 APIs
import finnhub
import fredpy as fp
from fredapi import Fred
from openai import OpenAI
#personal 파일
import config
import utilTool
#FAST API 관련
import logging
from fastapi import HTTPException, Request, APIRouter
from fastapi.responses import JSONResponse

# 라우터 설정
logging.basicConfig(level=logging.DEBUG)
frControllerETC = APIRouter()

# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
fp.api_key =config.FRED_API_KEY
fred = Fred(api_key=config.FRED_API_KEY)
rapidAPI = config.RAPID_API_KEY

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

##################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [2.채권가격 차트] Starts ##################################
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
    return {'data': chart_data, 'layout': chart_layout}

def show_base_rate():
    # 데이터 가져오기 및 변환   #날짜 입력받는 건 나중에 하자
    start_date = '2000-01-01'
    end_date = '2023-02-01'
    data = get_base_rate(start_date, end_date)

    dates_converted, values = utilTool.convert_data_for_json(data)

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
@frControllerETC.post("/get_bonds_data")
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
@frControllerETC.get("/bond-news/{category}")
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
@frControllerETC.post("/translate")
async def translate_text(request: TranslateRequest):
    # GPT를 호출하여 번역하는 함수
    translated_title = translate_gpt(request.title)
    translated_content = translate_gpt(request.content)
    
    return {"title": translated_title, "content": translated_content}


##################################[1ST_GNB][2ND_MENU] 글로벌 주요경제지표 보여주기 [2.채권가격 차트] Ends ##################################
##################################[1ST_GNB][5TH_MENU] 증시 CALENDAR 보여주기 Starts #####################################################
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
##################################[1ST_GNB][5TH_MENU] 증시 CALENDAR 보여주기 ENDS #####################################################
##################################[1ST_GNB][6TH_MENU] IPO CALENDAR 보여주기 STARTS #####################################################

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
    
#print(get_ipo_calendar())
##################################[1ST_GNB][6TH_MENU] IPO CALENDAR 보여주기 ENDS #####################################################
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

    SYSTEM_PROMPT = ""
    if action == "translate":
        # 한국어로 번역하기에 대한 처리
        SYSTEM_PROMPT = "You are an expert in translation. Translate the title and content from the following JSON data into Korean. Return the translated content in the same JSON format, but only translate the title and content into Korean. Do not provide any other response besides the JSON format."
        gpt_result = await utilTool.gpt4_news_sum(g_news, SYSTEM_PROMPT)

    elif action == "opinions":
        # AI 의견보기에 대한 처리
        SYSTEM_PROMPT = "Given the provided news data, please provide your expert analysis and insights on the current market trends and future prospects. Consider factors such as recent developments, market sentiment, and potential impacts on various industries based on the news. Your analysis should be comprehensive, well-informed, and forward-looking, offering valuable insights for investors and stakeholders. Thank you for your expertise"
        digest_news = extract_title_and_content(g_news)        
        gpt_result = await utilTool.gpt4_news_sum(digest_news, SYSTEM_PROMPT)

    elif action == "summarize":
        # 내용 요약하기에 대한 처리
        SYSTEM_PROMPT = "You're an expert in data summarization. Given the provided JSON data, please summarize its contents systematically and comprehensively into about 20 sentences, ignoring JSON parameters unrelated to news articles."        
        digest_news = extract_title_and_content(g_news)
        gpt_result = await utilTool.gpt4_news_sum(digest_news, SYSTEM_PROMPT)

    elif action == "navergpt":
        # 네이버 뉴스에 대한 GPT 의견 묻기임 
        SYSTEM_PROMPT = "You have a remarkable ability to grasp the essence of written materials and are adept at summarizing news data. Presented below is a collection of the latest news updates. Please provide a summary of this content in about 10 lines. Additionally, offer a logical and systematic analysis of the potential effects these news items could have on the financial markets or society at large, along with a perspective on future implications."        
        digest_news = g_news
        gpt_result = await utilTool.gpt4_news_sum(digest_news, SYSTEM_PROMPT)        
        
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
##################################[1ST_GNB][4TH_MENU] 해외 증시 마켓 PDF 분석 Starts ###################################################

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
##################################[1ST_GNB][4TH_MENU] 해외 증시 마켓 PDF 분석 ENDS ################################################### 