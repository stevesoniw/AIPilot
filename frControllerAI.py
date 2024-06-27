#Basic 함수
import asyncio
import json
import random
import requests
import os
import numpy as np 
import aiofiles
from datetime import datetime, timedelta
# 상용 Util 함수들
from pydantic import BaseModel
import pandas as pd
import matplotlib
import markdown
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from functools import lru_cache
from bs4 import BeautifulSoup
from langchain_community.llms import OpenAI
from langchain.agents import load_tools, initialize_agent
#금융관련 APIs
import finnhub
import yfinance as yf
from openai import OpenAI as RealOpenAI
from serpapi import GoogleSearch
#personal 파일
import config
import utilTool
#FAST API 관련
import logging
from fastapi import Query, HTTPException, APIRouter
from fastapi.responses import JSONResponse

# 라우터 설정
logging.basicConfig(level=logging.DEBUG)
frControllerAI = APIRouter()

# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = RealOpenAI(api_key = config.OPENAI_API_KEY)

#################################[1ST_GNB][1ST_MENU] AI가 말해주는 주식정보  Starts #################################
############  [해외 종목 검색] - 한글로 검색시 영어 종목코드 리턴해주기 #################


class UserInput(BaseModel):
    userInputCN: str
@frControllerAI.post("/foreignStock/get-frstock-code/")
async def get_frstock_code(data: UserInput):
    llm = OpenAI(api_key=config.OPENAI_API_KEY)
    print("**********************************")
    print(data.userInputCN)  # 사용자 입력 값을 확인
    print("**********************************")
    tool_names = ["serpapi"]
    serpapi_api_key = config.SERPAPI_API_KEY
    google_search = load_tools(tool_names, serpapi_api_key=serpapi_api_key)
    
    stock_ticker_search_agent = initialize_agent(google_search,
                            llm,
                            agent="zero-shot-react-description",
                            verbose=True,
                            return_intermediate_steps=True,  ## return_intermediate_steps allows return value for feature use, for example the throught process and final response
                            )

    input_template = "What is the stock symbol for " + data.userInputCN + ". And please only return the stock symbol; for example if input is Amazon, only return AMZN. And please do not return in sentence."
    
    response = stock_ticker_search_agent(
        {
            "input": input_template
        }
    )
    print(response)
    print("==========================================================================================================")
    stockCode = response['output']
    print(stockCode)
    return {"stockCode": stockCode}



############  [GET NEWS INFO (해외뉴스정보) 및 (소셜정보)] #################
# Finnhub 해외 종목뉴스 
@frControllerAI.get("/foreignStock/financials/news/{ticker}")
async def get_financial_stockNews(ticker: str):
    try:
        #현재 날짜를 기준으로 Finnhub에서 데이터 조회 (일단 데이터없는 종목들이 많아서 3개월치 가져온다)
        Start_date_calen = (datetime.strptime(utilTool.get_curday(), "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d") # 현재 시점 - 3개월 
        End_date_calen = utilTool.get_curday()     
        recent_news = finnhub_client.company_news(ticker, _from=Start_date_calen, to=End_date_calen)
        return recent_news
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
### Finnhub earnings_calendar 유료결제(분기 150달러)가 되어야 사용가능할듯.(Finnhub중에서도 Estimates쪽 결재필요)
### Freekey는 1분기꺼밖에 안옴. 일단 막아놓고 야후꺼로 조합해서 쓴다 ㅠㅠ
'''@app.get("/api/get_earning_announcement/{ticker}")
def calculate_financial_metrics(ticker: str):
    # YoY계산을 위해서 현재 날짜 기준으로 1년 전의 날짜를 시작 날짜로 설정
    Start_date_calen = (datetime.strptime(get_curday(), "%Y-%m-%d") - timedelta(days=365)).strftime("%Y-%m-%d")
    # 현재 날짜를 종료 날짜로 설정
    End_date_calen = get_curday()
    # Finnhub API를 사용하여 earnings calendar 데이터 가져오기
    earnings_calendar = finnhub_client.earnings_calendar(_from=Start_date_calen, to=End_date_calen, symbol=ticker, international=False).get('earningsCalendar')

    # 결과를 저장할 딕셔너리
    results = {
        "revenue_YoY": "-",
        "revenue_QoQ": "-",
        "revenue_beat_miss_ratio": "-",
        "eps_YoY": "-",
        "eps_QoQ": "-",
        "eps_beat_miss_ratio": "-",
        "current_quarter_revenue": "-",
        "current_quarter_eps": "-",
        "current_year_quarter": get_quarter_from_date(get_curday())
    }

    # 데이터 정렬 (최신 순)
    sorted_earnings = sorted(earnings_calendar, key=lambda x: x['date'], reverse=True)
    
    if not sorted_earnings:
        return results  # 데이터가 없으면 빈 결과 반환
    
    # 최신 분기 데이터
    latest = sorted_earnings[0]
    results["current_quarter_revenue"] = latest.get("revenueActual", "-")
    results["current_quarter_eps"] = latest.get("epsActual", "-")
    
    # 이전 분기 및 작년 동일 분기 찾기
    previous_quarter, previous_year = None, None
    for earning in sorted_earnings[1:]:
        if previous_quarter is None and earning['quarter'] == latest['quarter'] - 1:
            previous_quarter = earning
        if previous_year is None and earning['quarter'] == latest['quarter'] and earning['year'] == latest['year'] - 1:
            previous_year = earning
        if previous_quarter and previous_year:
            break
    
    # YoY, QoQ 계산
    if previous_year:
        results["revenue_YoY"] = calculate_growth(latest['revenueActual'], previous_year['revenueActual'])
        results["eps_YoY"] = calculate_growth(latest['epsActual'], previous_year['epsActual'])
    if previous_quarter:
        results["revenue_QoQ"] = calculate_growth(latest['revenueActual'], previous_quarter['revenueActual'])
        results["eps_QoQ"] = calculate_growth(latest['epsActual'], previous_quarter['epsActual'])
    
    # Beat/Miss 비율
    results["revenue_beat_miss_ratio"] = calculate_beat_miss_ratio(latest['revenueActual'], latest['revenueEstimate'])
    results["eps_beat_miss_ratio"] = calculate_beat_miss_ratio(latest['epsActual'], latest['epsEstimate'])
    
    return results'''

############ [1ST_GNB][1ST_MENU][GET STOCK INFO (종목기본정보)] #################
# 최근 실적 YoY, QoQ 데이터. 야후꺼와 finnhub calendar 최근분기만 조합해서 다시만듬. . 
@frControllerAI.get("/foreignStock/financials/earningTable/{ticker}")
async def get_financial_earningTable(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        
        # 분기별 재무제표 데이터
        quarterly_financials = stock.quarterly_financials.fillna(0)
        
        # 가장 최근 분기 선택
        latest_quarter = quarterly_financials.columns[0]
        latest_financials = quarterly_financials[latest_quarter]
        
        # YoY 및 QoQ 계산을 위한 이전 분기 선택
        previous_year_quarter = quarterly_financials.columns[4]
        previous_quarter = quarterly_financials.columns[1]
        previous_year_financials = quarterly_financials[previous_year_quarter]
        previous_quarter_financials = quarterly_financials[previous_quarter]
        
        # 필요한 데이터 계산
        total_revenue = latest_financials.get('Total Revenue', np.nan)
        operating_income = latest_financials.get('Operating Income', np.nan)
        
        revenue_yoy = ((total_revenue - previous_year_financials.get('Total Revenue', np.nan)) / abs(previous_year_financials.get('Total Revenue', 1)) * 100) if previous_year_financials.get('Total Revenue') else np.nan
        operating_income_yoy = ((operating_income - previous_year_financials.get('Operating Income', np.nan)) / abs(previous_year_financials.get('Operating Income', 1)) * 100) if previous_year_financials.get('Operating Income') else np.nan
        
        revenue_qoq = ((total_revenue - previous_quarter_financials.get('Total Revenue', np.nan)) / abs(previous_quarter_financials.get('Total Revenue', 1)) * 100) if previous_quarter_financials.get('Total Revenue') else np.nan
        operating_income_qoq = ((operating_income - previous_quarter_financials.get('Operating Income', np.nan)) / abs(previous_quarter_financials.get('Operating Income', 1)) * 100) if previous_quarter_financials.get('Operating Income') else np.nan
        
        # 현재 날짜를 기준으로 Finnhub에서 데이터 조회
        
        recent_earnings = finnhub_client.company_earnings(ticker, limit=1)
        if recent_earnings:
            eps_actual = recent_earnings[0].get('actual', np.nan)
            eps_estimate = recent_earnings[0].get('estimate', np.nan)
            eps_beat_miss_ratio = ((eps_actual - eps_estimate) / abs(eps_estimate) * 100) if eps_estimate and eps_actual is not None else np.nan
        else:
            eps_actual, eps_estimate, eps_beat_miss_ratio = np.nan, np.nan, np.nan

        return {
            "latest_quarter_revenue": total_revenue,
            "latest_quarter_operating_income": operating_income,
            "revenue_yoy_percentage": revenue_yoy,
            "operating_income_yoy_percentage": operating_income_yoy,
            "revenue_qoq_percentage": revenue_qoq,
            "operating_income_qoq_percentage": operating_income_qoq,
            "eps_actual": eps_actual,
            "eps_estimate": eps_estimate,
            "eps_beat_miss_ratio": eps_beat_miss_ratio,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 반환할 데이터 모델 정의
class FinancialData(BaseModel):
    income_statement: dict
    quarterly_income_statement: dict
    additional_info: dict
    charts_data: dict
    
#AI가 말해주는 주식 정보 [#2 종목 기본 정보] 호출용
@frControllerAI.get("/foreignStock/financials/{ticker}", response_model=FinancialData)
def get_financials_and_metrics(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info
    try : 
        stock = yf.Ticker(ticker)
        info = stock.info
        # 연간 재무제표 데이터
        income_statement = stock.financials.T.head(5).sort_index(ascending=True)
        balance_sheet = stock.balance_sheet.T.head(5).sort_index(ascending=True)

        # 분기별 재무제표 데이터
        quarterly_income_statement = stock.quarterly_financials.T.head(5).sort_index(ascending=True)
        
        # 일단 데이터 자체가 없는 종목들이 많아서 빈 값으로 초기화
        required_columns = ['Total Revenue', 'Operating Income', 'Operating Margin', 'Net Income', 'EPS']
        for column in required_columns:
            if column not in income_statement.columns:
                income_statement[column] = np.nan  # 빈 값으로 컬럼 초기화

        # 연간 데이터 계산
        if 'Operating Income' in income_statement.columns and 'Total Revenue' in income_statement.columns:
            income_statement['Operating Margin'] = income_statement['Operating Income'] / income_statement['Total Revenue'].replace(0, np.nan)
        else:
            income_statement['Operating Margin'] = np.nan  
        if 'Net Income' in income_statement.columns and 'Common Stock' in balance_sheet.columns:
            income_statement['EPS'] = income_statement['Net Income'] / balance_sheet['Common Stock'].replace(0, np.nan)
            income_statement['ROE'] = income_statement['Net Income'] / balance_sheet['Stockholders Equity'].replace(0, np.nan)
        else:
            income_statement['EPS'] = np.nan  
            income_statement['ROE'] = np.nan  
        # 필요한 컬럼만 선택
        selected_columns = income_statement[required_columns]
        # 분기별 데이터 계산
        if 'Total Revenue' in quarterly_income_statement.columns:
            # 분기별 매출 성장률 계산
            revenue_growth_qoq = quarterly_income_statement['Total Revenue'].pct_change()
            # 결과를 백분율로 변환
            revenue_growth_qoq_percentage = revenue_growth_qoq * 100
            # 첫 번째 값을 NaN으로 설정
            revenue_growth_qoq_percentage.iloc[0] = np.nan
            # 계산된 성장률을 DataFrame에 추가
            quarterly_income_statement['Revenue Growth QoQ'] = revenue_growth_qoq_percentage
        else:
            quarterly_income_statement['Revenue Growth QoQ'] = np.nan  # 'Total Revenue' 컬럼이 없는 경우 처리

        # EPS, PBR 계산을 위한 유효성 검사
        current_price = info.get('currentPrice', np.nan)
        shares_outstanding = info.get('sharesOutstanding', np.nan)
        # EPS, PBR 계산
        eps = income_statement['EPS'].iloc[0] if 'EPS' in income_statement.columns and not income_statement['EPS'].empty else np.nan
        book_value_per_share = (balance_sheet['Stockholders Equity'].iloc[0] / shares_outstanding) if 'Stockholders Equity' in balance_sheet.columns and not balance_sheet['Stockholders Equity'].empty and shares_outstanding != 0 else np.nan
        per = current_price / eps if eps and not np.isnan(eps) and current_price else np.nan
        pbr = current_price / book_value_per_share if book_value_per_share and not np.isnan(book_value_per_share) and current_price else np.nan
        # 데이터 추출 전 유효성 검사
        total_assets = balance_sheet['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.columns and not balance_sheet['Total Assets'].empty else np.nan
        shareholder_equity = balance_sheet['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in balance_sheet.columns and not balance_sheet['Stockholders Equity'].empty else np.nan
        # 추가 정보 딕셔너리에 안전하게 값을 채워넣기
        financial_data = {
            'annual_data': income_statement.to_dict(),
            'quarterly_data': quarterly_income_statement.to_dict(),
            'additional_info': {
                '회사 이름': info.get('shortName'),
                '섹터': info.get('sector'),
                '현재가': current_price,
                '50일 평균가': info.get('fiftyDayAverage'),
                '52주 신고가': info.get('fiftyTwoWeekHigh'),
                '52주 신저가': info.get('fiftyTwoWeekLow'),
                '총 자산': total_assets,
                '자기자본': shareholder_equity,
                '시가총액': info.get('marketCap'),
                '발행주식 수': shares_outstanding,
                '총 부채': info.get('totalDebt', np.nan),
                '영업현금흐름': info.get('operatingCashflow', np.nan),
                'PER': per,
                'PBR': pbr
            }
        }
        # 차트 데이터 준비
        charts_data = {
            "annual_financials": {
                "years": list(income_statement.index),
                "revenue": list(income_statement['Total Revenue']) if 'Total Revenue' in income_statement.columns else [np.nan],
                "operating_income": list(income_statement['Operating Income']) if 'Operating Income' in income_statement.columns else [np.nan],
                "operating_margin": list(income_statement['Operating Margin']) if 'Operating Margin' in income_statement.columns else [np.nan],
                "net_income": list(income_statement['Net Income']) if 'Net Income' in income_statement.columns else [np.nan],
                "eps": list(income_statement['EPS']),
                "roe": list(income_statement['ROE']),
            },
            "quarterly_growth": {
                "quarters": list(quarterly_income_statement.index),
                "revenue": list(quarterly_income_statement['Total Revenue']) if 'Total Revenue' in quarterly_income_statement.columns else [np.nan],
                "revenue_growth": list(quarterly_income_statement['Revenue Growth QoQ']) if 'Revenue Growth QoQ' in quarterly_income_statement.columns else [np.nan],
            },
        }
        return {
                "income_statement": selected_columns.to_dict(),
                "quarterly_income_statement": quarterly_income_statement.to_dict(),
                "additional_info": financial_data,
                "charts_data": charts_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))        

#get_financials_and_metrics('ITTSF')

def save_data_to_file(data, filename):
    """데이터를 JSON 파일로 저장"""
    with open(filename, 'w') as f:
        json.dump(data, f)

def read_data_from_file(filename):
    """종목코드 JSON 파일에서 데이터"""
    with open(filename, 'r') as f:
        return json.load(f)

@lru_cache(maxsize=100)
def cached_stock_symbols(exchange: str, mic: str): 
    filename = f"batch/stockcode/{exchange}_symbols.json"
    # 파일이 존재하면, 파일에서 데이터 읽기
    if os.path.exists(filename):
        logging.info(filename)
        return read_data_from_file(filename)
    # 파일이 없으면 API 호출
    logging.info("====couldn't find file. creating one====")
    # symbols = finnhub_client.stock_symbols(exchange, mic=mic)
    nasdaq_symbol = finnhub_client.stock_symbols('US', mic='XNAS')
    nyse_symbol = finnhub_client.stock_symbols('US', mic='XNYS')
    result = nasdaq_symbol+nyse_symbol
    # type = Common Stock 으로 REIT나 ETF 등은 제거함
    symbols = [stock for stock in result if stock['type'] == 'Common Stock' or stock['type'] == 'ADR']
    symbols_filtered = [{'symbol': sym['symbol'], 'description': sym['description']} for sym in symbols]
    # 데이터를 파일에 저장
    save_data_to_file(symbols_filtered, filename)
    return symbols_filtered

# 종목코드 읽기. Finnhub 에서 읽어오다가 도저히 느려서 안되겠음. 파일로 저장해서 읽는다. 
@frControllerAI.get("/api/get_foreign_stock_symbols")
def get_stock_symbols(q: str = Query(None, description="Search query"), mic: str = Query(default="", description="Market Identifier Code")):
    try:
        logging.info("======getting stock symbol=======")
        symbols_filtered = cached_stock_symbols('US', mic)
        if q:
            symbols_filtered = [sym for sym in symbols_filtered if q.lower() in sym['description'].lower() or q.lower() in sym['symbol'].lower()]
        return symbols_filtered
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
### 종목 Total INFO 만들어주기
async def get_news_info(ticker):
    params = {
    "engine": "google_news",
    "q": "pizza",
    "api_key": config.SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    news_results = results["news_results"]
    return news_results    

async def get_finance_info(ticker):
    params = {
        "engine": "google_finance",
        "q": ticker,
        "api_key": config.SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
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

@frControllerAI.get("/foreignStock/financials/getTotalInfo/{ticker}")
async def get_foreign_stock_totalinfo(ticker: str):
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
        
        gpt_result = await get_data_from_gpt(prompt)
        summary = markdown.markdown(gpt_result)
        
        # 파일 저장
        try:
            directory = f'batch/stocknews/{ticker}'
            today_date = datetime.now().strftime("%Y%m%d")
            filename = f"{ticker}_basicinfo_{today_date}.txt"
            
            os.makedirs(directory, exist_ok=True)
            filepath = os.path.join(directory, filename)
            
            with open(filepath, "w", encoding='utf-8') as file:
                file.write(summary)
        except Exception as e:
            print(f"File total stock info failed :: {ticker}: {e}")
        
        return {"summary": summary}
    
    except Exception as e:
        print(f"Failed to process {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process the ticker information.")
    
############ [1ST_GNB][1ST_MENU][GET EARNING INFO (실적발표)] #################
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
        #model="gpt-4-0125-preview",
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
    
async def get_historical_eps(ticker, limit=4):
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

async def get_stock_data_daily(symbol):
    EndDate = datetime.now()
    StartDate = utilTool.get_one_year_before(EndDate)
    stock_data = yf.download(symbol, start=StartDate.strftime('%Y-%m-%d'), end=EndDate.strftime('%Y-%m-%d'))
    return stock_data[["Adj Close", "Volume"]]

@frControllerAI.get("/api/charts/both/{ticker}")
async def get_both_charts(ticker: str):
    # 주식 실적 이력 차트 생성 및 Base64 인코딩
    fig1 = await get_historical_eps(ticker)
    earnings_chart_base64 = utilTool.get_chart_base64(fig1)
    
    # 애널리스트 추천 트렌드 차트 생성 및 Base64 인코딩
    fig2 = await get_recommend_trend(ticker)
    recommendations_chart_base64 = utilTool.get_chart_base64(fig2)
    todayDate = datetime.now().strftime("%Y%m%d")

    # 저장할 데이터 구성
    data_to_save = {
        "earnings_chart": earnings_chart_base64,
        "recommendations_chart": recommendations_chart_base64
    }
    # 파일 저장 디렉토리 경로 생성
    directory = f'batch/earning_data/{ticker}'
    os.makedirs(directory, exist_ok=True)

    # 데이터를 JSON 파일로 비동기적으로 저장
    file_path = f'{directory}/earningChart_{ticker}_{todayDate}.json'
    async with aiofiles.open(file_path, 'w') as file:
        await file.write(json.dumps(data_to_save))

    # 동일한 데이터를 클라이언트로 반환
    return JSONResponse(content=data_to_save)
  
@frControllerAI.get("/api/analysis/{ticker}")
async def get_analysis(ticker: str):
    result = query_gpt4(ticker)
    todayDate = datetime.now().strftime("%Y%m%d")
    #파일로도 한번 저장시킨다 (클라에서 파일 있으면 파일먼저 읽게)
    directory = f'batch/earning_data/{ticker}'
    os.makedirs(directory, exist_ok=True)
    file_path = f'{directory}/gptAnalysis_{ticker}_{todayDate}.json'
    async with aiofiles.open(file_path, 'w') as file:
        await file.write(json.dumps(result))

    return JSONResponse(content=result)
 
@frControllerAI.get("/api/stockwave/{ticker}")
async def get_stockwave(ticker: str):
    data = await get_stock_data_daily(ticker)
    logging.info(f"종목코드: {ticker}")
    print("******************************")
    print(data)
    # 날짜, 가격, 거래량을 각각 리스트로 변환
    dates = data.index.strftime('%Y-%m-%d').tolist()
    prices = data['Adj Close'].round(2).tolist()  # 소수점 두 자리로 반올림
    volumes = data['Volume'].tolist()

    return JSONResponse(content={
        "dates": dates,
        "prices": prices,
        "volumes": volumes,
    })

##################################[1ST_GNB][1ST_MENU] AI가 말해주는 주식정보 ENDS ###############################

