#Basic 함수
import json
import requests
import httpx
from urllib.parse import quote 
import asyncio
from typing import List, Dict, Optional
from typing import Optional
# 기존 Util 함수들
from pydantic import BaseModel
import pandas as pd
import numpy as np 
import matplotlib
matplotlib.use('Agg')
from bs4 import BeautifulSoup, NavigableString
#금융관련 APIs
import finnhub
import yfinance as yf
from openai import OpenAI
from dtaidistance import dtw
#personal 파일
import config
import utilTool
#config 파일
import config
#FAST API 관련
import logging
from fastapi import Query,HTTPException, APIRouter

# 라우터 설정
logging.basicConfig(level=logging.DEBUG)
dmController = APIRouter()

# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
############################## [2ND_GNB][1ST_MENU] 국내 뉴스정보 구현 ::  네이버 검색 API + 금융메뉴 스크래핑 활용 Starts ######################

#1. 네이버 검색 API
@dmController.get("/api/search-naver")
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
    
@dmController.get("/naver-scraping-news/", response_model=List[NewsItem])    
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
@dmController.post("/api/news-detail")
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
    
@dmController.post("/groqLamaTest")
async def groq_cloud_lama_test(request_data: dict):
    action = request_data.get("action")
    g_news = request_data.get("g_news")

    SYSTEM_PROMPT = ""
    if action == "navergpt":
        # 네이버 뉴스에 대한 GPT 의견 묻기임 
        SYSTEM_PROMPT = "You have a remarkable ability to grasp the essence of written materials and are adept at summarizing news data. Presented below is a collection of the latest news updates. Please provide a summary of this content in about 10 lines. Additionally, offer a logical and systematic analysis of the potential effects these news items could have on the financial markets or society at large, along with a perspective on future implications. answer in Korean."        
        digest_news = g_news
        print("***********************************")
        print(digest_news)
        
        gpt_result = await utilTool.lama3_news_sum(digest_news, SYSTEM_PROMPT)        
        
        print("return***************************************")
        print(gpt_result)
        
    else:
        gpt_result = {"error": "Invalid action"}
    
    return {"result": gpt_result}    
############################## [2ND_GNB][1ST_MENU] 국내 뉴스정보 구현 ::  네이버 검색 API + 금융메뉴 스크래핑 활용 시작 Ends ######################    

############################## [2ND_GNB][2ND_MENU] 국내 뉴스정보 구현 ::  국내 주식종목 유사국면 찾기 화면 개발 Starts   ################################
#일단 종목코드 갖고오는것부터 구현하자
@dmController.get("/stock-codes/")    
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
@dmController.post("/stock-chart-data")
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

@dmController.post("/find-similar-period")
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
    
    hist_full.index = hist_full.index.tz_localize(None)
    hist_ref.index = hist_ref.index.tz_localize(None)
    
    # 참조 기간의 인덱스 찾기
    ref_start_idx = hist_full.index.searchsorted(hist_ref.index[0])
    ref_end_idx = hist_full.index.searchsorted(hist_ref.index[-1], side='right') - 1
  
   
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
############################## [2ND_GNB][2ND_MENU] 국내 뉴스정보 구현 ::  국내 주식종목 유사국면 찾기 화면 개발 Ends   ################################