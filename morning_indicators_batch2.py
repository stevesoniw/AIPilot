# Util 함수들
import asyncio
import logging
from pathlib import Path
import datetime
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import seaborn as sns
import os
import aiofiles
#금융관련 APIs
from openai import OpenAI
import pandas_datareader.data as web
import yfinance as yf
#config 파일
import config



# API KEY 설정
client = OpenAI(api_key = config.OPENAI_API_KEY)
logging.basicConfig(level=logging.DEBUG)

sns.set_theme(style="whitegrid") 
path = 'mainHtml/assets/fonts/KoPubMedium.ttf' 
font_prop = fm.FontProperties(fname=path, size=12).get_name()
plt.rc('font', family=font_prop)
plt.rc('axes', unicode_minus=False) 

##################################################################################################################
#@@ 기능정의 : 고객상품전략팀에서 요청한 예시 차트 내용들을 파일로 떨구는 배치파일 by son (24.04.13)
#@@ Logic   : 1. datareader 와 yf 로 데이터 가져옴
#@@         ** → 폴더위치:: /batch/fred_indicators
#@@         ** → 파일이름:: {indicator_id}_chart.png
##################################################################################################################

def fetch_and_process_data():
    start = datetime.datetime(1980, 1, 1)
    end = datetime.datetime(2024, 12, 31)

    # Fetch data for unemployment, natural unemployment, and payroll
    unrate = web.DataReader("UNRATE", "fred", start, end)
    natural_unrate = web.DataReader("NROU", "fred", start, end)
    payroll = web.DataReader("PAYEMS", "fred", start, end).diff()
    sp500 = yf.download(tickers=['^GSPC'], start=start, end=end).resample('MS').first()

    # Fetch T10Y2Y and NASDAQ100 data
    fred_ticker = "T10Y2Y"
    target_ticker = "NASDAQ100"
    fred_var = web.DataReader(fred_ticker, "fred", start, end).pct_change()
    target_var = web.DataReader(target_ticker, "fred", start, end)

    # Merge and clean all data
    merged = pd.concat([unrate, natural_unrate, payroll, sp500['Adj Close'], fred_var, target_var], axis=1).fillna(method='ffill')
    merged.columns = ['UNRATE', 'NATURAL_UNRATE', 'PAYEMS', 'S&P500', 'T10Y2Y', 'NASDAQ100']
    merged['SLACK'] = merged['UNRATE'] - merged['NATURAL_UNRATE']
    merged.dropna(inplace=True)

    return merged, fred_ticker, target_ticker

async def gpt4_chart_talk(response_data, series_name):
    try:
        SYSTEM_PROMPT = "You are an outstanding economist and chart data analyst. I'm going to show you chart data for specific economic indicators. Please explain in as much detail as possible and share your opinion on the chart trends. It would be even better if you could explain the future market outlook based on facts. And analyze the patterns of the data and its impact on society or the market, and share your opinion on it. Please mark the part you think is the most important with a red tag so that it appears in red."
        prompt = "다음이 system 이 이야기한 json형식의 " + str(series_name)+" 차트 데이터야. system prompt가 말한대로 분석해줘. 단 답변을 꼭 한국어로 해줘. 시계열 차트데이터 : " + str(response_data)
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
    
    
def plot_and_save_unrate1(merged):
    # Calculate return and filter data
    wnd = 24
    merged['Return'] = merged['S&P500'].pct_change(wnd).shift(-wnd)
    below_natural = merged[merged['UNRATE'] <= merged['NATURAL_UNRATE']]['Return']
    above_natural = merged[merged['UNRATE'] > merged['NATURAL_UNRATE']]['Return']

    # Plotting
    plt.figure(figsize=(12, 6))
    sns.kdeplot(below_natural, fill=True, label='실업률 <= 자연실업률')
    sns.kdeplot(above_natural, fill=True, label='실업률 > 자연실업률')
    plt.axvline(below_natural.mean(), color='blue', linestyle='--', label='Mean Below Natural')
    plt.axvline(above_natural.mean(), color='orange', linestyle='--', label='Mean Above Natural')
    plt.title('S&P 500 Return Distribution by Unemployment Rate')
    plt.xlabel('Return')
    plt.ylabel('Density')
    plt.legend()
    plt.grid(True)
    plt.savefig('batch/fred_indicators/UNRATE1_chart.png')
    plt.close()

def plot_and_save_unrate2(merged):
    # Calculating slack
    merged['SLACK'] = merged['UNRATE'] - merged['NATURAL_UNRATE']
    positive_slack = merged['SLACK'].copy()
    positive_slack[positive_slack < 0] = np.nan
    negative_slack = merged['SLACK'].copy()
    negative_slack[negative_slack >= 0] = np.nan

    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.fill_between(merged.index, positive_slack, color='orange', alpha=0.5, label='Positive Slack')
    ax1.fill_between(merged.index, negative_slack, color='blue', alpha=0.5, label='Negative Slack')
    ax1.set_xlabel('날짜')
    ax1.set_ylabel('슬랙', color='purple')
    ax1.tick_params(axis='y', labelcolor='purple')
    ax1.set_title('SLACK (UNRATE - NATURAL UNRATE) and S&P 500 Index')
    ax1.legend(loc='upper left')
    ax1.grid(True)

    ax2 = ax1.twinx()
    ax2.plot(merged.index, merged['S&P500'], color='green', label='S&P 500')
    ax2.set_ylabel('S&P 500', color='green')
    ax2.tick_params(axis='y', labelcolor='green')
    ax2.legend(loc='upper right')

    plt.savefig('batch/fred_indicators/UNRATE2_chart.png')
    plt.close()
    
def plot_and_save_payems(merged):
    # Calculate and classify based on PAYEMS changes
    threshold = merged['PAYEMS'].quantile(0.1)
    below_threshold = merged[merged['PAYEMS'] <= threshold]['Return']
    above_threshold = merged[merged['PAYEMS'] > threshold]['Return']

    # Plotting PAYEMS
    plt.figure(figsize=(12, 6))
    sns.kdeplot(below_threshold, fill=True, label=f'고용 변화 <= {threshold:.2f}')
    sns.kdeplot(above_threshold, fill=True, label=f'고용 변화 > {threshold:.2f}')
    plt.title('PAYEMS: S&P 500 Return Distribution by Employment Changes')
    plt.legend()
    plt.savefig('batch/fred_indicators/PAYEMS_chart.png')
    plt.close()
    
def plot_and_save_t10y2y(merged, fred_ticker, target_ticker):
    wnd = 252
    merged['Return'] = merged[target_ticker].pct_change(wnd).shift(-wnd)
    threshold = merged[fred_ticker].quantile(0.1)
    below_threshold = merged[merged[fred_ticker] <= threshold]['Return']
    above_threshold = merged[merged[fred_ticker] > threshold]['Return']

    plt.figure(figsize=(12, 6))
    sns.kdeplot(below_threshold, fill=True, label=f'{fred_ticker} <= {threshold:.2f}')
    sns.kdeplot(above_threshold, fill=True, label=f'{fred_ticker} > {threshold:.2f}')
    plt.title(f'{target_ticker} Return Distribution by {fred_ticker}')
    plt.xlabel('Return')
    plt.ylabel('Density')
    plt.legend()
    plt.grid(True)
    plt.savefig('batch/fred_indicators/T10Y2Y_chart.png')
    plt.close()
    
def plot_and_save_sp500_vs_cpi():
    sns.set_theme(style="darkgrid")  # Setting the seaborn style to whitegrid

    # Fetch and process S&P 500 and CPI data
    start_date = '1977-01-01'
    end_date = '2023-12-31'
    sp500_data = yf.download('^GSPC', start=start_date, end=end_date)
    cpi_data = web.DataReader('CPIAUCNS', 'fred', start=start_date, end=end_date).pct_change(periods=12) * 100

    # Create a figure with dual axes
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(sp500_data.index, sp500_data['Adj Close'], color='deepskyblue', label='S&P 500 Index')
    ax1.set_yscale('log')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('S&P 500 Index', color='deepskyblue')
    ax1.tick_params(axis='y', labelcolor='deepskyblue')

    ax2 = ax1.twinx()
    ax2.plot(cpi_data.index, cpi_data['CPIAUCNS'], color='coral', label='Inflation (CPI)')
    ax2.set_ylabel('Inflation (CPI) %', color='coral')
    ax2.tick_params(axis='y', labelcolor='coral')
    ax2.axhline(y=5.3, color='red', linestyle='--', label='Inflation Threshold (5.3%)')

    plt.title('S&P 500 Index vs. Inflation (CPI)')
    plt.legend(loc='upper left')
    plt.savefig('batch/fred_indicators/SP500_VS_CPI_chart.png')
    plt.close()    

def prepare_chart_data(merged_data):
    if 'Return' not in merged_data.columns:
        merged_data['Return'] = merged_data['S&P500'].pct_change(periods=12).shift(-12)  # Yearly return

    # Round the data to five decimal places where applicable
    merged_data = merged_data.round(5)

    # Fetch S&P 500 and CPI data for sp500_vs_cpi chart
    start_date = '1977-01-01'
    end_date = '2023-12-31'
    sp500_data = yf.download('^GSPC', start=start_date, end=end_date)
    cpi_data = web.DataReader('CPIAUCNS', 'fred', start=start_date, end=end_date).pct_change(periods=12) * 100

    # Round the downloaded data as well
    sp500_data = sp500_data.round(5)
    cpi_data = cpi_data.round(5)

    data_dict = {
        "UNRATE1": {
            "data": merged_data[['UNRATE', 'Return']].dropna().to_dict(orient='list'),
            "description": "Unemployment rate and S&P 500 return distribution."
        },
        "UNRATE2": {
            "data": merged_data[['SLACK', 'S&P500']].dropna().to_dict(orient='list'),
            "description": "Slack based on unemployment and S&P 500 index data."
        },
        "PAYEMS": {
            "data": merged_data[['PAYEMS', 'Return']].dropna().to_dict(orient='list'),
            "description": "PAYEMS change and its impact on S&P 500 returns."
        },
        "T10T2Y": {
            "data": merged_data[['T10Y2Y', 'Return']].dropna().to_dict(orient='list'),
            "description": "T10Y2Y spread and NASDAQ100 return distribution."
        },
        "SP500_VS_CPI": {
            "data": {
                "sp500": sp500_data['Adj Close'].dropna().tolist(),
                "cpi": cpi_data['CPIAUCNS'].dropna().tolist()
            },
            "description": "Comparison between S&P 500 index and CPI inflation data."
        }
    }
    return data_dict

def clean_text(input_text):
    # Replace or remove the zero-width space
    cleaned_text = input_text.replace('\u200b', '')
    return cleaned_text

def fetch_chart_data_for_gpt4():
    merged_data, _, _ = fetch_and_process_data()
    chart_data = prepare_chart_data(merged_data)
    return chart_data

async def save_gpt4_chart_data(series_name, response_data):
    try:
        analysis = await gpt4_chart_talk(response_data, series_name)
        analysis = analysis.replace('\u200b', '')
        if analysis is not None:
            # Save the analysis to a text file
            async with aiofiles.open(f'batch/fred_indicators/{series_name}_gpt4.txt', 'w', encoding='utf-8') as f:
                await f.write(analysis)
            print(f"Data analysis for {series_name} saved successfully.")
        else:
            print(f"Failed to retrieve data analysis for {series_name}.")
    except Exception as e:
        print(f"An error occurred while processing {series_name}: {e}")
        
async def process_chart_data():
    try:
        # Fetch chart data
        chart_data = fetch_chart_data_for_gpt4()
        tasks = []
        for series_name, response_data in chart_data.items():
            tasks.append(save_gpt4_chart_data(series_name, response_data))
        # Execute tasks asynchronously
        await asyncio.gather(*tasks)
        print("All data analysis saved successfully.")
    except Exception as e:
        print(f"An error occurred while processing chart data: {e}")        

def main():
    try:
        merged_data, fred_ticker, target_ticker = fetch_and_process_data()
        plot_and_save_unrate1(merged_data)
        plot_and_save_unrate2(merged_data)
        plot_and_save_payems(merged_data)
        plot_and_save_t10y2y(merged_data, fred_ticker, target_ticker)
        plot_and_save_sp500_vs_cpi()

        asyncio.run(process_chart_data())
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
