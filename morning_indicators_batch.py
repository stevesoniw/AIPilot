# Util 함수들
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import json
import math
#금융관련 APIs
import fredpy as fp
from fredapi import Fred
from openai import OpenAI
#config 파일
import config
import os


# API KEY 설정
fp.api_key =config.FRED_API_KEY
fred = Fred(api_key=config.FRED_API_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
logging.basicConfig(level=logging.DEBUG)


# json 파일 저장할 경로 설정
base_path = Path("batch/fred_indicators")

if not os.path.exists(base_path):
    os.makedirs(base_path)

##################################################################################################################
#@@ 기능정의 : 해외주요경제지표들에 대해 API를 활용하여 미리 차트 json및 AI 의견을 생성해놓는 배치파일 by son (24.03.30)
#@@ Logic   : 1. Fred API로 주요지수 데이터를 얻어옴
#@@            - CPI(소비자물가지수), 개인소비지출(PCE), 생산자물가지수(PPI), 연방기금금리, 주택가격지수
#@@            - 실질 GDP, 명목 GDP, 고용비용지수(ECI), 실업률, 조정된 통화기초, 재정스트레스지수
#@@            - 미국 금리변동 추이, 국채선물이자율 (3개월, 2년, 10년)
#@@         : 2. 해당 지수 흐름에 대한 GPT 의견 호출. 요약 정리. 
#@@         ** → 최종적으로 이것을 fsIndicator.js 에서 불러와서 aiMain.html 에 넣어준다.     
#@@         ** → 폴더위치:: /batch/fred_indicators
#@@         ** → 파일이름:: {indicator_id}.json , {indicator_id}_aitalk.txt  
##################################################################################################################

# 지표 목록
indicators = {
    "DGS10": {"name": "미국채 10년이자율", "start_date": "2010-01-01"},
    "DGS2": {"name": "미국채 2년이자율", "start_date": "2010-01-01"},
    "DGS3MO": {"name": "미국채 3개월이자율", "start_date": "2010-01-01"},    
    "CPIAUCSL": {"name": "미국 소비자물가지수", "start_date": None},
    "PCEPI": {"name": "미국 개인소비지출지수", "start_date": None},
    "PPIFID": {"name": "미국 생산자물가지수", "start_date": None},
    "DFEDTARU": {"name": "미국 연방기금금리", "start_date": None},
    "CSUSHPISA": {"name": "미국 주택가격지수", "start_date": "1987-01-01"},
    "GDPC1": {"name": "미국 실질국내총생산", "start_date": "2000-01-01"},
    "ECIWAG": {"name": "미국 고용비용지수", "start_date": "2001-01-1"},
    "STLFSI4": {"name": "미국 금융스트레스지수", "start_date": None},
    "NGDPSAXDCUSQ": {"name": "미국 명목 국내총생산", "start_date": None},
    #"DCOILBRENTEU": {"name": "crude oil 가격", "start_date": "2000-01-01"},
    "GFDEGDQ188S": {"name": "미국 GDP 대비 공공부채 비율", "start_date": None},
    "MEHOINUSA672N": {"name": "미국 실질 중위 가구소득", "start_date": None},
    "INDPRO": {"name": "미국 산업생산지수", "start_date": None},
    #"SP500": {"name": "S&P500 지수", "start_date": "2000-01-01"},
    "UNRATE": {"name": "미국 실업률", "start_date": None},
    "FEDFUNDS": {"name": "미국 금리", "start_date": None}
}

# GPT4 에 차트데이터 분석을 요청하는 공통함수
async def gpt4_chart_talk(response_data, series_name):
    try:
        SYSTEM_PROMPT = "You are an outstanding economist and chart data analyst. I'm going to show you annual chart data for specific economic indicators. Please explain in as much detail as possible and share your opinion on the chart trends. It would be even better if you could explain the future market outlook based on facts. And analyze the patterns of the data and its impact on society or the market, and share your opinion on it. Please mark the part you think is the most important with a red tag so that it appears in red."
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

# series id 받아서 데이터 갖고오는 공통함수 
async def fetch_and_save_series_data(series_id, series_name, start_date=None):
    try:
        # FRED에서 데이터 가져오기
        data = fred.get_series(series_id)
        
        # 특정 시점부터 최근 데이터까지만 가져오기
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d') if isinstance(start_date, str) else start_date
            data = {date: value for date, value in data.items() if date >= start_date and not math.isnan(value)}
        else:
            # NaN 값이 있는 경우 해당 항목을 제외하고 저장
            data = {date: value for date, value in data.items() if not math.isnan(value)}
        
        # 데이터를 Highcharts가 읽을 수 있는 형식으로 변환
        formatted_data = [{"date": date.strftime('%Y-%m-%d'), "value": value} for date, value in data.items()]
        
        # JSON 파일로 저장
        file_path = base_path / f"{series_id}.json"
        with file_path.open("w") as f:
            json.dump(formatted_data, f)
        #batch\fred_indicators\UNRATE1_gpt4.txt
        # 추가적인 분석을 위해 gpt4_chart_talk 함수 사용
        analysis_result = await gpt4_chart_talk(formatted_data, series_name)
        # 분석 결과를 JSON 파일로 저장
        analysis_file_path = base_path / f"{series_id}_aitalk.txt"
        with analysis_file_path.open("w", encoding='utf-8') as f:
            f.write(analysis_result)            
            
    except Exception as e:
        logging.error(f"Error fetching or saving data for {series_name}: {e}")


# 모든 지표에 대해 함수 실행
async def main():
    tasks = []
    for series_id, series_info in indicators.items():
        start_date = series_info["start_date"]
        task = asyncio.ensure_future(fetch_and_save_series_data(series_id, series_info["name"], start_date))
        tasks.append(task)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
    
'''async def test():
    figData = await fetch_and_save_series_data("GDPC1", "미국 실질국내총생산", "2010-01-01")
    print(figData)
asyncio.run(test())'''

