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
import config
import utilTool
#FAST API 관련
import logging


# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)

####################################################################################################################################
#@@ 기능정의 : AI솔루션 PILOT웹사이트의 메인화면에서 부를 html 을 생성하는 파일 by son (24.03.10)
#@@ Logic   : 1. yfinance 로부터 주요지수(dow,nasdqa등) 데이터를 얻어옴
#@@         : 2. 해당 데이터들로부터 차트를 생성해 이미지로 떨궈놓음
#@@         : 3. 네이버 해외증시 사이트로부터 주요 뉴스들을 스크래핑 해옴
#@@         : 4. 주요지수 데이터와 네이버 뉴스를 gpt 에 던져서 AI daily briefing 가져옴
#@@         : 5. Finnhub로 부터 밤 사이 뉴스를 따로 받아옴
#@@         : 6. Finnhub 뉴스를 gpt 에 던져서 요약. 정리함
#@@         : 7. a)주요지수 b)차트이미지 c)AI briefing, d)네이버뉴스타이틀요약
#@@              d)Finnhub 뉴스  e) Finnhub 요약 데이터들을 모아 html로 생성 (*파일형식 :mainHtml\main_summary\summary_2024-03-30.html)
#@@          ** → 최종적으로 이것을 chat_pilot.html 에서 불러와 div에 꽂아준다.
#@@         : 8. 추가적으로 해외주식 종목코드를 finnhub(*stock_symbols) 통해서 가져와 파일로 떨궈놓는다.(batch\stockcode\US_symbols.json)
#####################################################################################################################################

# GPT4 에 뉴스요약을 요청하는 공통함수
async def gpt4_news_sum(newsData, SYSTEM_PROMPT):
    try:
        prompt = "This is the 'news data' mentioned by the system. Execute as instructed by the system prompt. However, please make sure to respond in Korean. Your response will be displayed on an HTML screen. Therefore, include appropriate <br> tags and other useful tags to make it easy for people to read. Please provide your perspective with a <span> tag. Also, you can insert a special icon(e.g., ★) when the subject of the content changes. 'News data':" + str(newsData)
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
        '^DJI': '다우지수', '^IXIC': '나스닥종합', '^GSPC': 'S&P500', '^KS11': 'KOSPI', '^FTSE': '영국 FTSE100',
        '^FCHI': '프랑스 CAC40', '^GDAXI': '독일 DAX', '^N225': '니케이 225', '000001.SS': '상해종합', 
        '^HSI': '항셍', 'DX-Y.NYB': '미국 USD', '^SOX': '필라델피아 반도체', 'CL=F': 'WTI 지수'
    }
    market_summary = []
    summary_talk = []
    images_name = []  
    
    image_dir = 'mainHtml/main_chart'
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
    SYSTEM_PROMPT_1 = "Here is the financial news from the past few hours. I will also provide you with financial data, including the Dow Jones, NASDAQ, and S&P 500 indices. Based on this financial news and index data, please analyze the current stock market and deeply consider your forecast for the future. Simply summarizing the market indices is not meaningful. Think and analyze like a financial expert, considering various news and changes in index data, and provide a meaningful opinion."
    # (이런형태임):: 너는 매우 뛰어난 뉴스 분석가이자 금융 전문가야. 다음은 지난 몇시간 동안의 금융 뉴스야.  또 나는 너에게 다우존스, 나스닥, S&P 500 지수 등의 금융 데이터도 같이 알려줄거야.  이 금융뉴스와 지수 데이터를 기반으로해서 현재 주식시장에 대해 분석해주고, 앞으로의 너의 전망에 대해서도 심도있게 고민해서 설명해줘.  단순히 시장 지수를 요약해주는 것은 의미가 없어. 여러가지 뉴스와 지수데이터의 변화에 대해서 금융 전문가답게 생각하고 분석해서 의미있는 의견을 제시해줘 
    gpt_summary = await gpt4_news_sum({"news": naver_news_data, "market_summary": summary_talk}, SYSTEM_PROMPT_1)
    #formatted_gpt_summary = gpt_summary.replace("-", "<br>")
    formatted_gpt_summary = re.sub(r"\*\*(.*?)\*\*", r"★<b>\1</b> ", gpt_summary)
    SYSTEM_PROMPT_2 = "You are an exceptionally talented news analyst and translator. Please translate the following news into Korean, individually for each piece of news. If the news is related to the financial markets in any way, feel free to share your opinion on it briefly. Also, no matter how much data there is, please try to translate everything and respond to the end. Translate the title and content and respond systematically. respond title, content, and your opinion on them only, nothing else."
    gpt_additional_news = await gpt4_news_sum({"news": finnhub_news_data}, SYSTEM_PROMPT_2)
    #formatted_additional_news = gpt_additional_news.replace("-", "<br>")
    formatted_additional_news = re.sub(r"```html\s*(.*?)\s*```", r"\1", gpt_additional_news)
    formatted_additional_news = re.sub(r"\*\*(.*?)\*\*", r"★<b>\1</b> ", formatted_additional_news)
    formatted_additional_news = re.sub(r"(\d+)\.", r"<br>\1.", formatted_additional_news)    
    
    print(gpt_additional_news)
    return formatted_gpt_summary, market_data, images_name, naver_news_data, formatted_additional_news

def format_text(input_text):
    # 볼드 처리
    formatted_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", input_text)
    # 파란색 별표 처리
    formatted_text = re.sub(r"### (.*?)", r"★<span style='color: blue;'>\1</span>", formatted_text)
    return formatted_text

# 메인페이지 로딩때마다 부르면 속도이슈가 있어서, html 파일로 미리 떨궈놓자. 
async def market_data():
    gpt_summary, market_data, images_name, naver_news_data, gpt_additional_news = await generate_market_summary()
    
    # Initialize the HTML content with the main structure
    html_content = f"""
    <main class="clear">
        <section class="fixed-cont v01">
            <div class="overlay"></div>
            <div class="tit-wrap" data-aos="fade-down" data-aos-duration="500">
                <h2 class="main-tit">MiraeAsset <span>M</span>orning <span>B</span>riefing</h2>
                <h3 class="sub-tit">해당 사이트는 AI Science팀에서 <span>"채권부문, Equtiy솔루션본부, 고객자산배분본부, 디지털리서치팀"</span>의 의견을 바탕으로 테스트 개발중입니다.</h3>
            </div>
            <div class="scroll-ic" data-aos="fade-right" data-aos-delay="500"></div>
        </section>
        
        <section class="general-cont bg-lightgrey">
            <h4 class="cont-tit" data-aos="fade-up">Market Summary</h4>
                <table data-aos="fade-up">
                    <caption>market summary morning brief</caption>
                    <thead>
                        <tr>
                            <th class="bg-white" scope="col"></th>"""

    market_names = [data["name"] for data in market_data]  # Extract market names
    for name in market_names:
        html_content += f'<th scope="col">{name}</th>'
    html_content += "</tr></thead><tbody>"

    keys = ["change", "prev_close", "last_close", "date"]
    for key in keys:
        html_content += f"<tr><td>{key.capitalize()}</td>"
        for data in market_data:
            value = data[key]
            color = "black"  # Default color
            if key == "change":
                if "-" in value:
                    color = "blue"
                elif value != "0.00%":
                    color = "red"
            if key == "last_close" and "change" in data:
                color = "blue" if "-" in data["change"] else "red" if data["change"] != "0.00%" else "black"
            html_content += f'<td style="color:{color};">{utilTool.format_number_with_comma(value)}</td>'
        html_content += "</tr>"
    
    html_content += """
                    </tbody>
                </table>"""

    # Dynamically add images
    html_content += '<ul class="main-graph-wrap" data-aos="fade-up">'
    for name, image in zip(market_data, images_name):
        html_content += f"""
                        <li>
                            <img src="/static/main_chart/{image}" alt="Market Chart">
                            <div class="chart-label-wrap">
                                <p>{name["name"]}</p>
                                <p>(종가: {utilTool.format_number_with_comma(name["last_close"])})</p>
                            </div>
                        </li>"""
    html_content += """
                    </ul>
            </section>"""

    # Add AI Market Analysis
    html_content += f"""
            <section class="general-cont fixed-cont v02">
                <div class="overlay v02"></div>
                <div class="analysis-wrap">
                    <div class="analysis-area">
                        <div class="analysis-tit-wrap">
                            <h4 class="cont-tit" data-aos="fade-right">AI Market <span>Analysis</span></h4>
                            <div class="analysis-bg" data-aos="fade-right"></div>
                        </div>
                        <div class="analysis-text" data-aos="fade-left">
                            {gpt_summary}
                        </div>
                    </div>
                </div>
            </section>"""

    # Add News Section
    html_content += """
            <section class="general-cont bg-lightgrey">
                <div class="news-wrap">
                    <h4 class="cont-tit" data-aos="fade-up">근거자료<br />Market Major News</h4>
                    <ul class="new-list" data-aos="fade-up">"""
    for news in naver_news_data:
        html_content += f"""
                        <li>
                            <p>{news['title']}</p>
                            <p>{news['summary']}</p>
                        </li>"""
    html_content += """
                    </ul>
                </div>
            </section>"""

    # Add Additional News Section
    html_content += f"""
            <section class="general-cont bg-green">
                <div class="finnhub-wrap">
                    <h4 class="cont-tit" data-aos="fade-left">기타 해외뉴스<br />Finnhub News</h4>
                    <div class="finnhub-list" data-aos="fade-right">
                        {gpt_additional_news}
                    </div>
                </div>
            </section>
        </main>"""

    # Save the HTML content to a file
    file_path = f'mainHtml/main_summary/summary_{datetime.now().strftime("%Y-%m-%d")}.html'
    with open(file_path, "w", encoding='utf-8') as file:
        file.write(html_content)

# 아침마다 Finnhub에서 종목리스트 읽어온 후 파일로 저장시킨다.
async def get_foreign_stock_symbols():
    try:
        exchange = "US"
        mic = ""  #Market Identifier Code
        code_dir = 'batch/stockcode'
        if not os.path.exists(code_dir):
            os.makedirs(code_dir)
        filename = f"{code_dir}/{exchange}_symbols.json"
        symbols = finnhub_client.stock_symbols(exchange, mic=mic)
        symbols_filtered = [{'symbol': sym['symbol'], 'description': sym['description']} for sym in symbols]
        utilTool.save_data_to_file(symbols_filtered, filename)
    except Exception as e:
        logging.error("An error occurred in making finnhub stock code file: %s", str(e))
        return None
    
async def morning_batch():
    make_morning_batch = await market_data()
    make_stock_symbols = await get_foreign_stock_symbols()
    print(make_morning_batch)
    print(make_stock_symbols)
asyncio.run(morning_batch())