#Basic 함수
from datetime import date, datetime, timedelta
import requests
import html
# 기존 Util 함수들
from pandas_datareader import data as pdr
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import os
import asyncio
import re
import json
from typing import List, Tuple
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import pearsonr
import scipy.stats
#금융관련 APIs
import finnhub
import yfinance as yf
from openai import OpenAI
from dtaidistance import dtw
#개인 클래스 파일 
import config
import utilTool
#FAST API 관련
import logging
from fastapi.responses import JSONResponse


# API KEY 설정
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
CONTROLLER = True
####################################################################################################################################
#@@ 기능정의 : AI솔루션 PILOT웹사이트의 메인화면에서 부를 마켓지수 유사국면 차트를 을 생성하는 파일 by son (24.05.08)
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
        '^DJI': '다우지수', '^IXIC': '나스닥종합', '^GSPC': 'S&P500', '^KS11': 'KOSPI' 
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

def fs_have_overlap(range1, range2):
    start1, end1, _ = range1
    start2, end2, _ = range2
    return start1 <= end2 and start2 <= end1

def fs_remove_overlaps(ranges):
    non_overlapping = [ranges[0]]
    for r1 in ranges[1:]:
        overlap = False
        for r2 in non_overlapping:
            if fs_have_overlap(r1, r2):
                overlap = True
                break
        if not overlap:
            non_overlapping.append((pd.to_datetime(r1[0]), pd.to_datetime(r1[1]), r1[2])) # Start, End, Distance
    return non_overlapping

def fs_get_start_end_score(df, dateScore, target_distance):
    result = []
    for from_date in dateScore:
        score = dateScore[from_date]
        started_data = df.loc[from_date:][:target_distance]
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        to_date = started_data.index[-1]
        result.append((from_date, to_date, score))
    return result

def fs_compute_distance(df: pd.DataFrame, target_input: Tuple[str, str], compare_input: Tuple[str, str], target_distance: int) -> dict:
    matrix = {}
    target_data = df.loc[target_input[0]: target_input[1]]
    target_data = target_data / target_data.values[0]
    target_values = np.array(target_data.values).reshape(-1)
    target_values -= target_values[0]
    compare_data = df.loc[compare_input[0]: compare_input[1]]

    for i in range(len(compare_data) - target_distance + 1):
        sliced_data = compare_data.iloc[i: i + target_distance, 0]
        sliced_data = sliced_data / sliced_data.values[0]
        compare_values = np.array(sliced_data).reshape(-1)
        compare_values -= compare_values[0]
        distance = dtw.distance_fast(target_values, compare_values, window = int(target_distance * 0.2), inner_dist = 'squared euclidean')
        pearson_corr = scipy.stats.pearsonr(target_values, compare_values)[0]
        matrix[sliced_data.index[0].strftime("%Y-%m-%d")] = (1 / (1 + distance)) * 0.5 + 0.5 * abs(pearson_corr)
    return matrix


def fs_create_figure(sample_data, target_date, selected_data, values_list, subtract=False, n_steps = 0):

    chart_data = {
        "chart": {"type": "line"},
        "title": {"text": "Graphs"},
        "xAxis": {"categories": []},
        "yAxis": {"title": {"text": "Value"}},
        "series": []
    }

    if n_steps > 0:
        get_length = len(sample_data.loc[target_date[0]: target_date[1]])
        target_data = sample_data[target_date[0]:][: get_length + n_steps]
        target_data.reset_index(drop=True, inplace=True)
    else:
        target_data = sample_data.loc[target_date[0]: target_date[1]]
        target_data.reset_index(drop=True, inplace=True)

    if subtract:
        target_trace = (target_data[selected_data] / target_data[selected_data].iloc[0])
        target_trace = (target_trace - target_trace[0])
    else:
        target_trace = target_data[selected_data]

    chart_data["xAxis"]["categories"] = target_data.index.tolist()
    chart_data["series"].append({"name": f"Target: {target_date[0]} to {target_date[1]}", "data": target_trace.tolist()})

    for i, (start_date, end_date, score) in enumerate(values_list, 1):
        if n_steps > 0:
            get_length = len(sample_data.loc[start_date:end_date])
            sliced_data = sample_data[start_date:][:get_length + n_steps]
            sliced_data.reset_index(drop=True, inplace=True)
        else:
            sliced_data = sample_data.loc[start_date:end_date]
            sliced_data.reset_index(drop=True, inplace=True)

        if subtract:
            sliced_trace = (sliced_data[selected_data] / sliced_data[selected_data].iloc[0])
            sliced_trace = (sliced_trace - sliced_trace[0])
        else:
            sliced_trace = sliced_data[selected_data]

        chart_data["series"].append({"name": f"Graph {i}: {start_date} to {end_date} ({round(score, 5)})", "data": sliced_trace.tolist()})

    return json.dumps(chart_data)

def draw_chart_from_json(json_data, ticker_name):
    data = json.loads(json_data)

    # Create the figure
    fig = go.Figure()

    # Extract chart details
    title_text = data['title']['text']
    x_axis_categories = data['xAxis']['categories']
    
    # Adding series to the chart
    for series in data['series']:
        fig.add_trace(go.Scatter(
            x=x_axis_categories,
            y=series['data'],
            mode='lines+markers',
            name=series['name']
        ))

    # Update layout with titles and labels
    fig.update_layout(
        title=title_text,
        xaxis_title="Index",
        yaxis_title="Value",
        template="plotly_white"
    )

    # Define the file path for the image
    today_date = datetime.now().strftime('%Y%m%d')
    file_path = f"mainHtml/main_chart/similar_{ticker_name}_{today_date}.png"

    # Ensure directory exists
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Save the figure
    fig.write_image(file_path)
    print(f"Chart saved to {file_path}")

    
def analyze():
    target_start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    target_end_date = datetime.now().strftime('%Y-%m-%d')
    analysis_start_date = "2000-01-01"
    analysis_end_date = (datetime.now() - timedelta(days=91)).strftime('%Y-%m-%d')   

    target_date = [target_start_date, target_end_date]
    compare_date =  [analysis_start_date, analysis_end_date]
            
    # Tickers dictionary
    tickers = {
        '^DJI': '다우지수', 
        #'^IXIC': '나스닥종합', 
        #'^GSPC': 'S&P500', 
        #'^KS11': 'KOSPI'
    }
    ticker = '^DJI'
    n_steps = 20
    n_graphs = 1
    threshold = 0.5
    
    # Download data using yfinance
    df = yf.download(list(tickers.keys()), start=analysis_start_date, end=target_end_date)

    # Ensure df is a DataFrame, even if only one column is downloaded
    if isinstance(df, pd.Series):
        df = df.to_frame()  # Convert Series to DataFrame
    df = df[['Close']].rename(columns={'Close': '다우지수'})
    df.index = pd.to_datetime(df.index)
    df.sort_index(ascending=True, inplace=True)
    print("Data after download and processing:")
    print(df)
    
    
    target_distance = len(df.loc[target_date[0]: target_date[1]])

    similarity_scores = fs_compute_distance(df, target_date, compare_date, target_distance)
    start_end_distance_list = fs_get_start_end_score(df, similarity_scores, target_distance)
    start_end_distance_list = sorted(start_end_distance_list, key=lambda x: x[2], reverse=CONTROLLER)
    filtered_start_end_distance_list = fs_remove_overlaps(start_end_distance_list)

    filtered_start_end_distance_list = [entry for entry in filtered_start_end_distance_list if entry[2] >= threshold][:n_graphs]

    selected_data = '다우지수'    

    fs_superimpose_target_original = fs_create_figure(df, target_date, selected_data, filtered_start_end_distance_list, subtract=False, n_steps = n_steps)
    fs_superimpose_target_aligned = fs_create_figure(df, target_date, selected_data, filtered_start_end_distance_list, subtract=True, n_steps = n_steps)

    print(fs_superimpose_target_original)
    print("********************")
    print(fs_superimpose_target_aligned)
    print("********************")
    
    #chart_data = {
    #    "original": fs_superimpose_target_original.to_json(),
    #    "aligned": fs_superimpose_target_aligned.to_json()
    #}
    draw_chart_from_json(fs_superimpose_target_aligned, "dow")    
    
    return JSONResponse(content={
        "chart_data": {
            "original": fs_superimpose_target_original,  
            "aligned": fs_superimpose_target_aligned     
        }
    })  
print(analyze())


    
'''async def morning_batch():
    make_morning_batch = await market_data()
    make_stock_symbols = await get_foreign_stock_symbols()
    print(make_morning_batch)
    print(make_stock_symbols)
asyncio.run(morning_batch())'''