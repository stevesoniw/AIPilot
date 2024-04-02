#Basic 함수
from datetime import date, datetime, timedelta
import requests
import html
# 기존 Util 함수들
from bs4 import BeautifulSoup
from pandas_datareader import data as pdr
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import os
import asyncio
import re
#금융관련 APIs
import finnhub
import yfinance as yf
from openai import OpenAI
#개인 클래스 파일 
#config 파일
import config
#FAST API 관련
import logging


# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)

####################################################################################
#@@ 기능정의 : AI솔루션 PILOT웹사이트의 메인화면에서 부를 html 을 생성하는 파일 by son (24.03.10)
#@@ Logic   : 1. yfinance 로부터 주요지수(dow,nasdqa등) 데이터를 얻어옴
#@@         : 2. 해당 데이터들로부터 차트를 생성해 이미지로 떨궈놓음
#@@         : 3. 네이버 해외증시 사이트로부터 주요 뉴스들을 스크래핑 해옴
#@@         : 4. 주요지수 데이터와 네이버 뉴스를 gpt 에 던져서 AI daily briefing 가져옴
#@@         : 5. Finnhub로 부터 밤 사이 뉴스를 따로 받아옴
#@@         : 6. Finnhub 뉴스를 gpt 에 던져서 요약. 정리함
#@@         : 7. a)주요지수 b)차트이미지 c)AI briefing, d)네이버뉴스타이틀요약
#@@              d)Finnhub 뉴스  e) Finnhub 요약 데이터들을 모아 html로 생성
#@@          ** → 최종적으로 이것을 chat_pilot.html 에서 불러와 div에 꽂아준다.     
####################################################################################

# GPT4 에 뉴스요약을 요청하는 공통함수
async def gpt4_news_sum(newsData, SYSTEM_PROMPT):
    try:
        prompt = "다음이 system 이 이야기한 뉴스 데이터야. system prompt가 말한대로 실행해줘. 단 답변을 꼭 한국어로 해줘. 너의 전망에 대해서는 red color로 보이도록 태그를 달아서 줘. 뉴스 데이터 : " + str(newsData)
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

def get_main_marketdata():
    yf.pdr_override()
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    tickers = {
        '^DJI': '다우지수', '^IXIC': '나스닥종합', '^GSPC': 'S&P500', '^KS11': 'KOSPI',
        '^FTSE': '영국 FTSE100', '^FCHI': '프랑스 CAC40', '^GDAXI': '독일 DAX', 'DX-Y.NYB': '미국 USD',
        '^SOX': '필라델피아 반도체', 'CL=F': 'WTI 지수'
    }
    market_summary = []
    summary_talk = []
    images_name = []  
    
    image_dir = 'chartHtml/main_chart'
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
            
    for ticker, name in tickers.items():
        df = pdr.get_data_yahoo(ticker, start_date)
        df.reset_index(inplace=True)
        
        # 일단 마지막 두 날짜 데이터만 가져와 변화량을 계산하자
        last_day = df.iloc[-1]
        prev_day = df.iloc[-2]
        change = (last_day['Adj Close'] - prev_day['Adj Close']) / prev_day['Adj Close'] * 100
        summary_for_gpt = f"{name} 지수는 전일 대비 {change:.2f}% 변화하였습니다. 전일 가격은 {prev_day['Adj Close']:.2f}이며, 오늘 가격은 {last_day['Adj Close']:.2f}입니다."
        summary = {
            "name": name,
            "change": f"{change:.2f}%",
            "prev_close": f"{prev_day['Adj Close']:.2f}",
            "last_close": f"{last_day['Adj Close']:.2f}",
            "date": last_day['Date'].strftime('%Y-%m-%d')
        }        
        market_summary.append(summary)
        summary_talk.append(summary_for_gpt)

        # 차트 생성 코드. 4개만 생성한당
        if name in ['다우지수', '나스닥종합', 'S&P500', 'KOSPI']:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Adj Close'], mode='lines', line=dict(color='red'), name='Adj Close'))
            fig.update_layout(
                title=name,
                xaxis_title='Date',
                yaxis_title='Price',
                template='plotly_dark',
                autosize=False,
                width=800,
                height=600,
                margin=dict(l=50, r=50, b=100, t=100, pad=4)
            )
            # 이미지 저장 로직 
            image_path = f"{image_dir}/{name}_{datetime.now().strftime('%Y-%m-%d')}.png"
            fig.write_image(image_path)
            images_name.append(image_path.split('/')[-1])

    return market_summary, images_name, summary_talk

# 네이버 해외뉴스가 젤 깔끔한듯. 내용도 좀 있고. 이거 스크래핑 해요자
async def naver_global_news_scraping():
    # 웹 페이지 URL
    url = 'https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258&section_id3=403'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 'newsList' 클래스를 가진 모든 'li' 항목을 찾습니다.
    news_lists = soup.find_all('li', class_='newsList')
    
    results = []
    
    for news_list in news_lists:
        articles = news_list.find_all(['dt', 'dd'], class_='articleSubject')
        
        for article in articles:
            title = None
            summary = None
            if article.a:
                title = article.a.get('title', '').strip()
            # 해당 기사의 요약 추출을 위한 로직 수정
            summary_tag = article.find_next_sibling('dd', class_='articleSummary')
            if summary_tag:
                summary_full = ' '.join(summary_tag.text.strip().split())
                if "..." in summary_full:
                    summary = summary_full.split("...")[0].strip() + "..."  #언론사 제거. 메인에서 보여주기 좀 별로.
                else:
                    summary = summary_full + "..."
            
            if title and summary:
                results.append({
                    'title': title,
                    'summary': summary
                })
                
    return results

#따로 보여줄 밤사이 글로벌 뉴스. 일단 Finnhub꺼 씀. 
async def get_finnhub_marketnews() :
    market_news = finnhub_client.general_news('general', min_id=0)
    return market_news

async def generate_market_summary():
    naver_news_data = await naver_global_news_scraping()
    finnhub_news_data = await get_finnhub_marketnews()  
    market_data, images_name, summary_talk = get_main_marketdata()
    
    # gpt4_news_sum 함수에 전달할 데이터 준비
    SYSTEM_PROMPT_1 = "You are an exceptionally talented news analyst and a finance expert. Here is the financial news from the past few hours. Also, I will provide you with data on the changes in the Dow Jones, NASDAQ, and S&P 500 indices. Based on this financial news and index data, please analyze the current stock market and deeply consider and explain your forecast for the future."
    # (이런형태임):: 너는 매우 뛰어난 뉴스 분석가이자 금융 전문가야. 다음은 지난 몇시간 동안의 금융 뉴스야.  또 나는 너에게 다우존스, 나스닥, S&P 500 지수의 변화 데이터도 같이 알려줄거야.  이 금융뉴스와 지수 데이터를 기반으로해서 현재 주식시장에 대해 분석해주고, 앞으로의 너의 전망에 대해서도 심도있게 고민해서 설명해줘. 
    gpt_summary = await gpt4_news_sum({"news": naver_news_data, "market_summary": summary_talk}, SYSTEM_PROMPT_1)
    SYSTEM_PROMPT_2 = "You are an exceptionally talented news analyst and translator. Please translate the following news into Korean, individually for each piece of news. If the news is related to the financial markets in any way, feel free to share your opinion on it briefly. Also, no matter how much data there is, please try to translate everything and respond to the end. Translate the title and content and respond systematically. respond title, content, and your opinion on them only, nothing else."
    gpt_additional_news = await gpt4_news_sum({"news": finnhub_news_data}, SYSTEM_PROMPT_2)
    
    print(gpt_additional_news)
    return gpt_summary, market_data, images_name, naver_news_data, gpt_additional_news

def format_text(input_text):
    # 볼드 처리
    formatted_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", input_text)
    # 파란색 별표 처리
    formatted_text = re.sub(r"### (.*?)", r"★<span style='color: blue;'>\1</span>", formatted_text)
    return formatted_text

# 메인페이지 로딩때마다 부르면 속도이슈가 있어서, html 파일로 미리 떨궈놓자. 
async def market_data():
    gpt_summary, market_data, images_name, naver_news_data, gpt_additional_news = await generate_market_summary()
    
    # HTML 내용을 작성합니다.
    html_content = """
    <div class="main_summary_container">
        <div class="title_container">
            <h1 class="main_summary_title">Market Summary<span class="morning_brief">   - Morning Brief</span></h1>        
        </div>
        <div class="market_data_container">
            <div class="market_table_container">
                <table class="market_table">
                    <tr>
                        <th>Market</th>
                        <th>Change</th>
                        <th>Previous Close</th>
                        <th>Last Close</th>
                        <th>Date</th>
                    </tr>
    """
    for data in market_data:
        change_color = "blue" if "-" in data['change'] else "red"
        last_close_color = change_color
        # 특정 항목에 대한 배경색 설정
        bg_color = "#ebf5ff" if data['name'] in ["다우지수", "나스닥종합", "S&P500", "KOSPI"] else "none"

        html_content += f"""
                    <tr>
                        <td style='background-color:{bg_color};'>{data['name']}</td>
                        <td style='color:{change_color};'>{data['change']}</td>
                        <td>{data['prev_close']}</td>
                        <td style='color:{last_close_color};'>{data['last_close']}</td>
                        <td>{data['date']}</td>
                    </tr>
        """
    html_content += """
                </table>
            </div>
            <div class="main_summary_images">
    """
    # images_name 처리
    for path in images_name:
        market_name = path.split('_')[0]  # 파일 이름에서 시장 이름 추출
        last_close = next((item for item in market_data if item['name'] == market_name), {}).get('last_close', 'N/A')
        html_content += f"""
                <div class="market_chart">
                    <img src='/static/main_chart/{path}' alt='Market Chart'>
                    <div class="chart_labels_container">
                    <span class="chart_label">{market_name}</span> <span class="chart_label2"> (종가: {last_close})</span>
                    </div>
                </div>
        """   
    # gpt_summary 처리
    html_content += """
            </div>
        </div> """
    html_content += f"""
        <div class="gpt_summary">
            <h2 class="gpt_summary_title">AI Market Analysis</h2>
            <p>{format_text(gpt_summary.replace('\n', '<br/>'))}</p>
        </div>
        <div class="news_container">
           <div class="news_section">
            <button class="evidence_button">근거자료</button>
            <span class="news_text">- Market Major News</span>
           </div>
        """        
    # naver_news_data 처리
    for news in naver_news_data:
        html_content += f"""
            <div class="news_item">
                <p>{news['title']}</p>
                <p>{news['summary']}</p>
            </div>
        """
    html_content += """
        </div> 
    """
        # gpt_additional_news 처리
    temp_data = format_text(gpt_additional_news.replace('\n', '<br>'))
    html_content += f"""
        <div class="additional_news_container">
            <div class="additional_news_section">
                <button class="additional_news_button">기타 해외뉴스</button>
                <span class="finnhub_text">- From Finnhub news</span>
            </div>
            <div class="additional_news_item">
                {temp_data}
            </div>
        </div>
    </div>
    """

    # 결과를 HTML 파일로 저장
    file_path = f'mainHtml/main_summary/summary_{datetime.now().strftime("%Y-%m-%d")}.html'
    with open(file_path, "w", encoding='utf-8') as file:
        file.write(html_content)


async def cccc():
    earnings_chart = await market_data()
    print(earnings_chart)
asyncio.run(cccc())