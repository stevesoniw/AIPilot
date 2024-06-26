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
import markdown
#금융관련 APIs
import finnhub
import yfinance as yf
from openai import OpenAI
from serpapi import GoogleSearch
#개인 클래스 파일 
import config
import utilTool
#FAST API 관련
import logging

from wordcloud import WordCloud
from wordcloud import STOPWORDS


#import httpx


# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)

client = OpenAI(api_key = config.OPENAI_API_KEY)
#client = OpenAI(api_key = config.OPENAI_API_KEY , http_client= httpx.Client(verify=False))

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
        prompt = '''This is the "data" mentioned by the system. Execute as instructed by the system prompt. 
    However, please make sure to respond in Korean. Your response will be displayed on an HTML screen. 
    Therefore, include appropriate <br> tags and useful tags to make it easy for people to read.  
    If there are important keywords or sentences, wrap them in <strong> tags. (example: <strong>'주요문장'</strong>)
    However, do not write the CSS codes directly into the response and do not include the title separately in the response.  "data":''' + str(newsData)
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

async def get_main_marketdata():
    yf.pdr_override()
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    tickers = {
        '^DJI': '다우지수', '^IXIC': '나스닥종합', '^GSPC': 'S&P500', '^KS11': 'KOSPI', '^N225': '니케이 225', 
         '000001.SS': '상해종합', '^FTSE': '영국 FTSE100', '^FCHI': '프랑스 CAC40', '^GDAXI': '독일 DAX', 
        'DX-Y.NYB': '미국 USD', '^SOX': '필라델피아 반도체', 'CL=F': 'WTI 지수'
        #'^HSI': '항셍',
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
        change_price = last_day['Adj Close'] - prev_day['Adj Close'] 
        summary_for_gpt = f"{name} 지수는 전일 대비 {change:.2f}% 변화하였습니다. 전일 가격은 {prev_day['Adj Close']:.2f}이며, 오늘 가격은 {last_day['Adj Close']:.2f}입니다."
        summary = {
            "name": name,
            "change": f"{change:.2f}%",
            "change_price" : f"{change_price:.2f}",
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
                font=dict(family='NanumGothic', size=18),  # 네클에서 깨져서 폰트설치후 추가
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
    ### 가져오는 내용 중에 headline이랑 summary 만 가져와서 리스트에 저장한다
    formatted_news_list = []
    try: 
        for news in market_news:
            formatted_news_list.append({
                'title': news['headline'],
                'summary': news['summary']
            })
        return formatted_news_list
    except Exception as e:
        logging.error("An error occurred in get_finnhub_marketnews function: %s", str(e))
        return None
    # return market_news

#구글 마켓증시 index 및 trends api  
async def get_google_market_index() :
    params = {
    "engine": "google_finance_markets",
    "trend": "indexes",
    "api_key": config.SERPAPI_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    market_trends = results["market_trends"]
    return market_trends

## ```html ``` 코드블럭 제거하는 함수
def extract_text_from_html_code_block(text):
    match = re.search(r'```html(.*?)```', text, re.DOTALL)
    if match: ## gpt에 코드블럭 들어감. 코드블럭 안에 들어간 내용 추출
        return match.group(1).strip()
    else: ## 코드 블럭 없음. 그냥 텍스트 리턴
        return text
    
async def generate_market_summary():
    naver_news_data = await naver_global_news_scraping()
    finnhub_news_data = await get_finnhub_marketnews()  
    google_market_index = await get_google_market_index()
    market_data, images_name, summary_talk = await get_main_marketdata()
    
    ######### gpt4 로 요약 정리할 내용 던지기 ###############
    ########## 1. 뉴스요약 ##################
    
    # '''You are an exceptionally skilled news analyst and financial expert. The following is financial news from the past few hours. You need to summarize and organize this financial news clearly and systematically.
    # Summarize whether each news item is a Bull point, Bear point, or Neutral for the overall financial market and display this information in an HTML table.
    # The HTML table should have three categories: Bull, Bear, and Neutral. The header should always be in this order and format: "Bull (긍정)", "Bear (부정)", and "Neutral (중립)". List the content of each news item briefly and clearly under the appropriate category. Before the table, include overall status quo and outlook of the market given the bull, bear, neutral news in 2-3 sentences. In the summary, mention key events happening that would affect the financial market. The answer should start with the summary and end with the table.'''
    SYSTEM_PROMPT_1 = '''You are an exceptionally skilled news analyst and financial expert. The following is financial news from the past few hours. You need to summarize and organize this financial news clearly and systematically.
Summarize whether each news item is a Bull point, Bear point, or Neutral for the overall financial market and display this information in an HTML table.
The HTML table should have three categories: Bull, Bear, and Neutral. The header should always be in this order and format: "Bull (긍정)", "Bear (부정)", and "Neutral (중립)". List the content of each news item briefly and clearly under the appropriate category, and include <br> twice after each content to distinguish each content. Before the table, provide the overall market sentiment given the bull, bear, neutral news in 2-3 sentences. Start the summary with the following phrase: "오늘의 시장 상황: ". In the summary, mention key events happening that would affect the financial market. The answer should start with the summary and end with the table.'''
    # (이런형태임)::     너는 매우 뛰어난 뉴스 분석가이자 금융 전문가야. 다음은 지난 몇시간 동안의 금융 뉴스야.이 금융뉴스를 깔끔하고 체계적으로 정리해서 보여줘야해. 해당 뉴스가 전반적인 금융시장에 Bull 포인트 or Bear 포인트가 되는 뉴스인지 아닌지 정리 및 요약해서 표로 보여줘.    html 표 내에서 긍정적인 뉴스, 부정적인 뉴스, 기타 뉴스(=전반적인 금융시장에 영향을 주지 않는 뉴스)로 분리해서  해당 뉴스 내용을 아주 간단하고 
    #                   깔끔하게 나열해줘. 총평 부분을 html 테이블 내에 따로 행을 만들어서 전반적인 뉴스와 그 영향도에 따른 너의 의견도 1~2줄로 작성해줘.  
    news_summary = await gpt4_news_sum({"news data 1": naver_news_data, "news data 2": finnhub_news_data}, SYSTEM_PROMPT_1)
    # news_summary = re.sub(r"```html\s*(.*?)\s*```", r"\1", news_summary)
    print(news_summary)
    news_summary = markdown.markdown(extract_text_from_html_code_block(news_summary))
    print("****after markdown********")
    print(news_summary)
    
    ########## 2. 증시데이터와 엮어서 설명 ############
    SYSTEM_PROMPT_2 = '''
    너는 뛰어난 금융 전문가야. 다음은 현재 증시 index 데이터들이야. 
    해당 index 들의 상황에 대해서 체계적이고 깔끔하게 html 표형태로 요약해서 알려줘. 단 지수 데이터가 얼마나 변했는지를 하나하나 나열하면 안돼.
    미국지수는 전반적으로 어떻게 변했는지, 유럽과 아시아지수는 전반적으로 상승했는지 하락했는지 등 문장으로 깔끔하고 이해하기 쉽게 설명해줘. 
    화면상에 아주 체계적이고 깔끔하게 보여줄수 있게 답변을 주되 모든것을 깔끔하게 html 표로 만들어서 답변해줘.
    다음은 답변의 예시야.
      - 미국지수 : 다우지수와 나스닥은 조금 올랐지만 S&P는 적은 수치(0.02%)로 하락했습니다. 
      - 유럽지수 : 전반적으로 많이 상승했습니다. 독일 DAX(1.3% 상승)가 상승을 주도한 것으로 보입니다. 
      - 아시아지수 : KOSPI와 항셍지수는 크게 올랐지만 니케이가 소폭 하락했습니다.
      - OVERALL : 전반적으로 글로벌 상승장이 지속되고 있습니다. 
    '''
    index_summary = await gpt4_news_sum({"market index summary :": summary_talk, "market index total(json data)": google_market_index}, SYSTEM_PROMPT_2)    
    index_summary = re.sub(r"```html\s*(.*?)\s*```", r"\1", index_summary)
    index_summary = markdown.markdown(index_summary)
    
    ########## 3. 향후 시장분석 ############
    SYSTEM_PROMPT_3 = "You are an exceptional news analyst and financial expert. Here are the financial news and market data from the past few hours. There is no need to summarize or re-explain these news and index data. Based solely on this financial news and index data, analyze the current stock market and provide your in-depth outlook for the future. Think and analyze the various news and changes in index data as a financial expert, offering meaningful insights. Summarize only your deep and insightful opinions. Do not provide any other responses beyond the requested content."
    # (이런형태임)::너는 매우 뛰어난 뉴스 분석가이자 금융 전문가야. 다음은 지난 몇시간 동안의 금융 뉴스와 마켓데이터야. 이 뉴스 및 증시 데이터들을 요약하거나 다시 설명해줄 필요는 없어. 오로지 금융뉴스와 지수 데이터를 기반으로해서 현재 주식시장에 대해 분석해주고, 앞으로의 너의 전망에 대해서도 심도있게 고민해서 설명해줘.  여러가지 뉴스와 지수데이터의 변화에 대해서 금융 전문가답게 생각하고 분석해서 의미있는 의견을 제시해줘.  오로지 너의 깊이있고 통찰력있는 의견만을 정리해서 알려줘 
    opinion_summary = await gpt4_news_sum({"news": naver_news_data, "market_summary": summary_talk}, SYSTEM_PROMPT_3)   
    opinion_summary = re.sub(r"```html\s*(.*?)\s*```", r"\1", opinion_summary) 

    ########## 4. Finnhub 부가뉴스 번역 및 요약 ##########
    SYSTEM_PROMPT_4 = "You are an exceptionally talented news analyst and translator. Please translate the following news into Korean, individually for each piece of news. If the news is related to the financial markets in any way, feel free to share your opinion on it briefly. Also, no matter how much data there is, please try to translate everything and respond to the end. Translate the title and content and respond systematically. respond title, content, and your opinion on them only, nothing else."
    gpt_additional_news = await gpt4_news_sum({"news": finnhub_news_data}, SYSTEM_PROMPT_4)

    formatted_news_summary = re.sub(r"\*\*(.*?)\*\*", r"★<b>\1</b> ", news_summary)    
    formatted_index_summary = re.sub(r"\*\*(.*?)\*\*", r"★<b>\1</b> ", index_summary)  
    formatted_opinion_summary = re.sub(r"\*\*(.*?)\*\*", r"★<b>\1</b> ", opinion_summary)  
    #formatted_additional_news = gpt_additional_news.replace("-", "<br>")
    formatted_additional_news = re.sub(r"```html\s*(.*?)\s*```", r"\1", gpt_additional_news)
    formatted_additional_news = markdown.markdown(formatted_additional_news)
    formatted_additional_news = re.sub(r"\*\*(.*?)\*\*", r"★<b>\1</b> ", formatted_additional_news)
    formatted_additional_news = re.sub(r"(\d+)\.", r"<br>\1.", formatted_additional_news)    
    print(gpt_additional_news)

    await generate_word_cloud(naverNewsData=naver_news_data, finnhubNewsData=finnhub_news_data)

    return formatted_news_summary, formatted_index_summary, formatted_opinion_summary, market_data, images_name, naver_news_data, formatted_additional_news

# Title, Summary 를 한 스트링으로 묶는 함수
def combine_title_and_summary(data):
    # Data: [{'title': 'Mirae', 'summary': 'I love Mirae}, ...]
    combined_text = ""
    for item in data:
        title = item.get('title', '')
        summary = item.get('summary', '')
        combined_text += "Title: " + title + '\n' + "Content: " + summary + '\n\n'
    return combined_text.strip()


async def generate_word_cloud(naverNewsData, finnhubNewsData):

    SYSTEM_WORD_PROMPT = "You are an exceptionally talented news analyst and translator. Please translate the following news into Korean, individually for each piece of news. If the news is related to the financial markets in any way, feel free to share your opinion on it briefly. Also, no matter how much data there is, please try to translate everything and respond to the end. Translate the title and content and respond systematically. respond title, content, and your opinion on them only, nothing else."
    print("*******naver********")
    print(naverNewsData)
    # gpt_naver_word_cloud_message  = await gpt4_new_sum_word_cloud({"news": naverNewsData}, SYSTEM_WORD_PROMPT)
    # print("********************")
    # print(gpt_naver_word_cloud_message)

    today_date = datetime.now().strftime('%Y%m%d')

    file_path = f"mainHtml/main_word_cloud/news_word_cloud_{today_date}.png"

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    prompt = '''너는 문단 안에 핵심 키워드를 잘 찾는 전문가야. 너한테 뉴스 목록을 줄 건데, 각 뉴스마다 뉴스의 핵심 키워드를 3개씩 추출해.
    <Example>
        Title: 위험선호 속 ‘강달러’…환율, 장중 1370원 후반대로 소폭 상승
        Content: 원·달러 환율은 장중 1370원 후반대로 상승하고 있다. 위험자산 선호 회복에도 불구하고 달러화 강세에 환율이 상승 압력을 받고 있다. 사진=A...     

    Your answer: 강달러, 달러화, 환율상승
    
    답변은 항상 한국어로 줘. 두 단어여도 키워드면 띄어쓰지 마. 키워드는 명사여야 해. '애플이' (X) '애플' (O) 특파원 이름은 키워드로 넣지마. 2024, 2021년도최고 같은 연도는 키워드로 넣지마. 
    
    답변은 키워드만 나열해서 줘.
    The answer only contains the keywords.
    
    뉴스 목록:''' + str(combine_title_and_summary(naverNewsData))
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[                
            {"role": "user", "content": prompt}
            ],
        temperature=0.1
    )

    sample = completion.choices[0].message.content 

    await save_word_cloud(wordMessage=str(sample), width=1280, height=800, filePath= file_path)


    # gpt_finnhub_word_cloud_message  = await gpt4_new_sum_word_cloud({"news": finnhubNewsData}, SYSTEM_WORD_PROMPT)
    print("*******finnhub********")
    print(finnhubNewsData)
    file_path = f"mainHtml/main_word_cloud/finnhub_word_cloud_{today_date}.png"

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    prompt = '''I will give you news list. Your role is to extract 3 keywords from each article. 
    <Example>
    [Article]
    Title: Warren Buffett says this public speaking class changed his life—4 tips from the course
    Content: Warren Buffett cured his fear of public speaking with a Dale Carnegie Training course, which cost $100 at the time. Here are four lessons the class taught him.
    
    Your answer: Warren-Buffet, public-speaking
    
    The keyword should always be proper nouns. If the keyword consists of two words (ex. Warren Buffet), include hyphen to connect the two.
    
    You must not include common nouns (ex. long, pay, earnings) that does not qualify as main keywords of the news. Do not include verbs (spend, pay) in keywords.
    
    The answer only contains the keywords.
    
    News:''' + str(combine_title_and_summary(finnhubNewsData))
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[                
            {"role": "user", "content": prompt}
            ]
    )

    sample = completion.choices[0].message.content 

    await save_word_cloud(wordMessage=str(sample), width=1280, height=800, filePath= file_path)


async def save_word_cloud(wordMessage:str, width:int, height:int, filePath):
    print("*****printing keywords*****")
    print(wordMessage)
    ## 불용어 사전 추가
    # STOPWORDS.add("title'")
    # STOPWORDS.add("summary'")
    # STOPWORDS.add("...")
    STOPWORDS.add("Title")
    STOPWORDS.add("Content")
    STOPWORDS.add("stock")
    STOPWORDS.add("stocks")
    STOPWORDS.add("stock-market")
    STOPWORDS.add("economy")
    STOPWORDS.add("money")
    STOPWORDS.add("market")
    STOPWORDS.add("S&P-500")
    STOPWORDS.add("S")
    STOPWORDS.add("P")
    STOPWORDS.add("consumer")
    STOPWORDS.add("부사장")
    STOPWORDS.add("rate")
    STOPWORDS.add("개최")
    STOPWORDS.add("record")
    STOPWORDS.add("public")
    STOPWORDS.add("Keywords")
    STOPWORDS.add("키워드")
    STOPWORDS.add("U.S.")
    STOPWORDS.add("U")
    STOPWORDS.add("markdown")
    STOPWORDS.add("html")
    STOPWORDS.add("say")

    wordcloud = WordCloud(width=width, height=height, background_color='white', stopwords=STOPWORDS, font_path="./mainHtml/assets/fonts/NanumBarunGothic.ttf", normalize_plurals=True, include_numbers=False, regexp=r"\b\w[\w&']*\b").generate(wordMessage)    
    
    wordcloud.to_file(filePath)

    # plt.figure(figsize=(10, 5))
    # plt.imshow(wordcloud, interpolation='bilinear')   # wordcloud 객체를 넣으면 워드클라우드 형태의 그래프 생성
    # plt.axis('off')  #눈금 삭제 
    # #plt.show()
    # plt.savefig(filePath, format='png', bbox_inches='tight', pad_inches=0)
    # plt.close()    

async def gpt4_new_sum_word_cloud(newsData, SYSTEM_PROMPT):
    try:

        prompt = '''This is the "data" mentioned by the system. Execute as instructed by the system prompt. 
                    However, make sure to respond in Korean.  "data":''' + str(newsData)
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )

        # return completion.choices[0].message.content

        content = completion.choices[0].message.content
        print("***************")
        print(content)

        prompt = '''다음과 같은 문장에서 이름 또는 지명과 같은 고유 명사만 추출해서 응답으로 보여줄래.
                    다음:''' + str(content)
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[                
                {"role": "user", "content": prompt}
                ]
        )

        return completion.choices[0].message.content    
    
    except Exception as e:
        logging.error("An error occurred in gpt4_news_sum function: %s", str(e))
        return None


def format_text(input_text):
    # 볼드 처리
    formatted_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", input_text)
    # 파란색 별표 처리
    formatted_text = re.sub(r"### (.*?)", r"★<span style='color: blue;'>\1</span>", formatted_text)
    return formatted_text

# 메인페이지 로딩때마다 부르면 속도이슈가 있어서, html 파일로 미리 떨궈놓자. 
async def market_data():
    formatted_news_summary, formatted_index_summary, formatted_opinion_summary, market_data, images_name, naver_news_data, gpt_additional_news = await generate_market_summary()
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_date_fixed = datetime.now().strftime('%Y%m%d')
    # Initialize the HTML content with the main structure

    html_content = f"""
    <main class="clear">
        <section class="fixed-cont v01">
            <div class="overlay"></div>
            <div class="tit-wrap" data-aos="fade-down" data-aos-duration="500">
                <h2 class="main-tit">AI <span>M</span>orning <span>B</span>riefing</h2>
                <h3 class="sub-tit">해당 사이트는 AI Science팀에서 <span>"채권부문, Equity솔루션본부, 고객자산배분본부, 디지털리서치팀"</span>의 의견을 바탕으로 테스트 개발중입니다.</h3>
            </div>
            <div class="scroll-ic" data-aos="fade-right" data-aos-delay="500"></div>
        </section>
        <section class="general-cont bg-lightgrey">
            <h4 class="cont-tit" data-aos="fade-up">
                <span>Market Summary</span>
            </h4>
            <div data-aos="fade-up">
                <div class="main-tb-date">기준일 : {today_date}</div>
                <div class="main-new-tb">"""
                
    for i in range(1, 5):
        html_content += f"""
                    <table class="tb-bg0{i}">
                        <caption>Market Data Table {i}</caption>
                        <colgroup>
                            <col />
                            <col />
                            <col />
                            <col />
                        </colgroup>
                        <thead>
                            <tr>
                                <th scope="col">종목</th>
                                <th scope="col">등락률</th>
                                <th scope="col">전일 대비</th>
                                <th scope="col">종가</th>
                            </tr>
                        </thead>
                        <tbody>"""                

        for data in market_data[(i-1)*3:i*3]:  # Assuming 3 rows per table for simplicity
            change_color = 'red' if not '-' in data['change'] else 'blue'
            html_content += f"""
                            <tr>
                                <td>{data['name']}</td>
                                <td style="color:{change_color};">{data['change']}</td>
                                <td style="color:{change_color};">{utilTool.format_number_with_comma(data['change_price'])}</td>
                                <td style="color:{change_color};">{utilTool.format_number_with_comma(data['last_close'])}</td>
                            </tr>"""
        html_content += """
                        </tbody>
                    </table>"""

    html_content += """
                </div>
            </div>"""
            
    html_content += """
            <div data-aos="fade-up">
                <div class="main-graph-tit"><span>주요지수 3개월 추이 그래프</span></div>"""
            
    html_content += '<ul class="main-graph-wrap" data-aos="fade-up">'
    for data, image_name in zip(market_data, images_name):
        image_path = f"/static/main_chart/{image_name}"
        html_content += f"""
                    <li>
                        <img src="{image_path}" alt="Market Chart for {data['name']}">
                        <div class="chart-label-wrap">
                            <p>{data['name']}</p>
                            <p>(종가: {utilTool.format_number_with_comma(data["last_close"])})</p>
                        </div>
                    </li>"""

    html_content += """
                </ul>
            </div>"""  # Move </ul> outside the for loop
    html_content += f"""                
            <div class="flex-center">
                <div class="main-tb-box" data-aos="fade-up">            
                   <span>아래 차트는 유사패턴분석 알고리즘으로 최근 3개월 지표의 패턴과 가장 유사했던 과거 패턴을 찾아 비교 분석한 내용입니다.</span>
                    <ul class="main-graph-coment">
                        <li class="blue-square">: 최근 3개월 패턴,</li>
                        <li class="red-square">: 유사한 과거 패턴,</li>
                        <li class="yellow-square"> 이후: 과거 패턴의 이후 흐름</li>
                    </ul>
                    <div class="btn-wrap mt10">
                        <a href="/static/aiReal.html?menu=menu4_c" class="btn-common small btn-blue02">유사패턴분석 활용하기 &gt;</a>
                    </div>       
                </div>         
            </div>     
            <div class="main-summary-chart" data-aos="fade-up">
                <div class="main-summary-chart-box"><img src= "/static/main_chart/similar_DOW_{today_date_fixed}.png"></div>
                <div class="main-summary-chart-box"><img src= "/static/main_chart/similar_NASDAQ_{today_date_fixed}.png"></div>
                <div class="main-summary-chart-box"><img src= "/static/main_chart/similar_S&P500_{today_date_fixed}.png"></div>            
                <div class="main-summary-chart-box"><img src= "/static/main_chart/similar_KOSPI_{today_date_fixed}.png"></div>
            </div>   
        </section>"""
    html_content += f"""                                       
        <section class="general-cont fixed-cont v02">
            <div class="overlay v02"></div>
            <div class="analysis-wrap02">
                <h4 class="cont-tit aos-init aos-animate" data-aos="fade-up">
                    <span>AI Market Analysis</span>
                </h4>
                <div class="analysis-box-wrap" data-aos="fade-up">
                    <div class="analysis-box">
                        <h3 class="sub-tit">뉴스로 보는 투자 분위기</h3>
                        <div class="analysis-text vertop-table">     
                            {formatted_news_summary}
                        </div>            
                    </div>  
                    <div class="analysis-box">
                        <h3 class="sub-tit">지수로 보는 마켓 상황</h3>
                        <div class="analysis-text">
                            {formatted_index_summary}
                        </div>
                    </div>
                    <div class="analysis-box">
                        <h3 class="sub-tit">뉴스와 지수로 보는 AI 분석 예측</h3>
                        <div class="analysis-text">
                           <li>{formatted_opinion_summary}</li> 
                        </div>
                    </div>   
                </div>                                          
                <div class="news-show-wrap">
                    <p class="news-info-p">※ 매일 오전 07:00에 갱신됩니다.</p>
                </div>
             </div>
        </section>"""
    
    html_content += f"""<section id="majorNews" class="general-cont bg-lightgrey">
                            <h4 class="cont-tit">
                                <span>News Word Cloud</span>
                            </h4>
                            <div class="major-news-wrap">
                                <div class="national-news-wrap">
                                    <h3><span>국내뉴스 포털이 뽑은 주요뉴스 키워드</span></h3>
                                    <div class="mt20">
                                        <img src= "/static/main_word_cloud/news_word_cloud_{today_date_fixed}.png">
                                    </div>
                                </div>
                                <div class="oversea-news-wrap">
                                        <h3><span>해외뉴스 포털이 뽑은 주요뉴스 키워드</span></h3>
                                        
                                    <div class="mt20">
                                        <img src= "/static/main_word_cloud/finnhub_word_cloud_{today_date_fixed}.png">
                                    </div>
                                </div>
                            </div>
                            <div class="btn-wrap mt30">
                                <a href="/static/aiReal.html?menu=menuc" class="btn-common large btn-blue02">해외뉴스 보러가기 &gt;</a>
                            </div>
                        </section>                  
                      """                                     
    
    #         <div class="main-news-wrap" style="display:none;">
    #             <ul class="new-list">"""
    # for news in naver_news_data:
    #     html_content += f"""                              
    #                 <li>
    #                     <p>{news['title']}</p>
    #                     <p>{news['summary']}</p>
    #                 </li>"""
    # html_content += """
    #             </ul>
    #         </div>                    
                
    #     </section>"""
    # html_content += f"""        
    #     <section class="general-cont bg-lightpink sub-news-wrap" style="display:none;">
    #         <div class="finnhub-wrap">
    #             <h4 class="cont-tit" data-aos="fade-left">
    #                 <span>Finnhub News</span>
    #             </h4>
    #             <div class="finnhub-list" data-aos="fade-right">
    #                 {gpt_additional_news}
    #             </div>
    #         </div>
    #     </section>
        

    html_content += "</main>"

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
        # symbols = finnhub_client.stock_symbols(exchange, mic=mic)
        # 나스닥, 뉴욕증권소 두 개 에서만 종목명과 종목코드 불러오기 
        nasdaq_symbol = finnhub_client.stock_symbols('US', mic='XNAS')
        nyse_symbol = finnhub_client.stock_symbols('US', mic='XNYS')
        result = nasdaq_symbol+nyse_symbol
        # type = Common Stock 으로 REIT나 ETF 등은 제거함
        symbols = [stock for stock in result if stock['type'] == 'Common Stock']
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
