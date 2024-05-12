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
CONTROLLER = True
####################################################################################################################################
#@@ 기능정의 : AI솔루션 PILOT웹사이트의 메인화면에서 부를 마켓지수 유사국면 차트를 을 생성하는 파일 by son (24.05.08)
#@@ Logic   : 1. yfinance 로부터 주요지수(dow,nasdqa등) 2000년 이후의 데이터를 얻어옴
#@@         : 2. 해당 데이터들로부터 dtw 알고리즘을 이용해서 현재 3개월간 데이터와 가장 유사했던 기간을 뽑아옴
#@@         : 3. 이를 다우, 나스탁, S&P500, KOSPI 4개지수에 대해서 차트이미지로 생성해서 떨궈놓음
#@@         **  → mainHtml/main_chart/similar_{지수명}_{date.png} (예 : similar_나스닥종합_20240511.png)
#@@         : 4. (**진행하다가 포기) 해당 유사기간 날짜에 해당하는 글로벌 뉴스데이터를 Fetch해옴
#@@         : 5. (못함) GPT 에 유사국면 차트데이터와 뉴스데이터를 전달해서 이야기를 생성
#@@         : 6. (못함) 이야기를 txt로 저장 (추후 main화면에서 보여주도록..)
#@@             → 과거뉴스가 거의 안나와서 일단 포기. finnhub, seeking alpha 모두 2010년 이전은 뉴스데이터가 없다.
#@@             → 나중에 혹시 진행하게 된다면 KDI 경제전망사이트 같은데 분기별로 정리된 글로벌경제시황을 DB나 파일에 넣어놓고 이것을 읽게해야될듯함. 
#####################################################################################################################################

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



def fs_create_figure(sample_data, target_date, selected_data, values_list, subtract=True, n_steps=20):
    chart_data = {
        "chart": {"type": "line"},
        "title": {"text": "Graphs"},
        "xAxis": {"categories": []},
        "yAxis": {"title": {"text": "Value"}},
        "series": []
    }

    # Prepare the target data without n_steps extension
    target_data = sample_data.loc[pd.to_datetime(target_date[0]):pd.to_datetime(target_date[1])]
    target_data.reset_index(drop=True, inplace=True)
    target_trace = (target_data[selected_data] / target_data[selected_data].iloc[0] - 1) if subtract else target_data[selected_data]
    
    # Setting x-axis categories for the target data
    chart_data["xAxis"]["categories"] = list(range(len(target_data)))
    chart_data["series"].append({"name": f"Target: {target_date[0]} to {target_date[1]}", "data": target_trace.tolist()})

    # Process each comparable period, applying n_steps
    for i, (start_date, end_date, score) in enumerate(values_list, 1):
        start_date, end_date = pd.to_datetime(start_date), pd.to_datetime(end_date)

        # Extend end_date by n_steps for all graphs
        end_date += pd.Timedelta(days=n_steps)

        # Ensure the end_date does not exceed the data range
        end_date = min(end_date, sample_data.index.max())

        # Slicing the data according to the adjusted date range
        sliced_data = sample_data.loc[start_date:end_date]
        sliced_data.reset_index(drop=True, inplace=True)

        # Calculate the normalized or raw trace for each graph
        sliced_trace = (sliced_data[selected_data] / sliced_data[selected_data].iloc[0] - 1) if subtract else sliced_data[selected_data]

        # Extend the x-axis categories based on the length of sliced_data
        chart_data["xAxis"]["categories"] = list(range(len(sliced_data)))

        # Assembling the graph name with additional info
        graph_name = f"Graph {i}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} +{n_steps} days ({round(score, 2)})"
        chart_data["series"].append({"name": graph_name, "data": sliced_trace.tolist()})

    return json.dumps(chart_data)


def draw_chart_from_json(json_data, ticker_name):
    data = json.loads(json_data)

    fig = go.Figure()

    x_axis_categories = data['xAxis']['categories']
    max_x_length = len(x_axis_categories)
    first = True

    target_proportion = 90 / 110
    target_x_length = int(max_x_length * target_proportion)

    for series in data['series']:
        # 간소화된 정규식을 사용하여 날짜 추출
        date_pattern = r"\d{4}-\d{2}-\d{2}"
        dates = re.findall(date_pattern, series['name'])
        if dates and len(dates) >= 2:
            start_date, end_date = dates[:2]
        else:
            start_date = end_date = ''

        if first:
            x_categories = x_axis_categories[:target_x_length]
            y_data = series['data'][:target_x_length]
            color = '#0055ff'
        else:
            x_categories = x_axis_categories
            y_data = series['data']
            color = '#ff1480'

        name_suffix = ' <span style="color:#FFD700">+20 days</span>' if not first else ''
        name = f"{start_date} ~ {end_date}{name_suffix}"

        fig.add_trace(go.Scatter(
            x=x_categories,
            y=y_data,
            mode='lines',
            line=dict(color=color, width=3, shape='spline', smoothing=0.5),
            name=name
        ))

        if first:
            fig.add_shape(
                type="line",
                x0=target_x_length, y0=0, x1=target_x_length, y1=1,
                line=dict(color="#FFD700", width=2, dash="dash"),
                xref="x", yref="paper"
            )
        first = False

    fig.update_layout(
        title=f'{ticker_name} :: 과거 유사기간 비교',
        xaxis_title="Index",
        yaxis_title="Value",
        legend_title_text='',
        legend=dict(orientation="h", xanchor="center", x=0.5, y=-0.15),
        template="plotly_dark",
        plot_bgcolor='rgba(10,10,10,1)',
        paper_bgcolor='rgba(10,10,10,1)'
    )

    today_date = datetime.now().strftime('%Y%m%d')
    file_path = f"mainHtml/main_chart/similar_{ticker_name}_{today_date}.png"

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    fig.write_image(file_path)
    print(f"Chart saved to {file_path}")
    
   
def analyze():
    target_start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    target_end_date = datetime.now().strftime('%Y-%m-%d')
    analysis_start_date = "2000-01-01"
    analysis_end_date = (datetime.now() - timedelta(days=91)).strftime('%Y-%m-%d')   

    target_date = [target_start_date, target_end_date]
    compare_date = [analysis_start_date, analysis_end_date]
            
    tickers = {
        '^DJI': '다우지수', 
        '^IXIC': '나스닥종합', 
        '^GSPC': 'S&P500', 
        '^KS11': 'KOSPI'
    }

    n_steps = 20
    threshold = 0.5
    n_graphs = 1

    for ticker_symbol, ticker_name in tickers.items():
        print(f"Processing: {ticker_name}")

        df = yf.download(ticker_symbol, start=analysis_start_date, end=target_end_date)
        if isinstance(df, pd.Series):
            df = df.to_frame(name='Close')
        
        df = df[['Close']].rename(columns={'Close': ticker_name})
        df.index = pd.to_datetime(df.index)
        df.sort_index(ascending=True, inplace=True)        

        if not df.empty:
            target_distance = len(df.loc[target_date[0]: target_date[1]])

            similarity_scores = fs_compute_distance(df, target_date, compare_date, target_distance)
            start_end_distance_list = fs_get_start_end_score(df, similarity_scores, target_distance)
            start_end_distance_list = sorted(start_end_distance_list, key=lambda x: x[2], reverse=CONTROLLER)
            filtered_start_end_distance_list = fs_remove_overlaps(start_end_distance_list)
            filtered_start_end_distance_list = [entry for entry in filtered_start_end_distance_list if entry[2] >= threshold][:n_graphs]

            selected_data = ticker_name
            if filtered_start_end_distance_list:
                fs_superimpose_target_aligned = fs_create_figure(df, target_date, selected_data, filtered_start_end_distance_list, subtract=True, n_steps = n_steps)
                draw_chart_from_json(fs_superimpose_target_aligned, selected_data)    
            else:
                print(f"No significant patterns found for {ticker_name}")
        else:
            print(f"No data retrieved for {ticker_name}")

if __name__ == "__main__":
    analyze()
  
    
    
'''async def morning_batch():
    make_morning_batch = await market_data()
    make_stock_symbols = await get_foreign_stock_symbols()
    print(make_morning_batch)
    print(make_stock_symbols)
asyncio.run(morning_batch())'''