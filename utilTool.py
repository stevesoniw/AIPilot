from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
from pandas import Timestamp
from io import BytesIO
import math
import numpy as np
import base64
import json 
import logging
from openai import OpenAI
import config

# API KEY 설정

client = OpenAI(api_key = config.OPENAI_API_KEY)

# 현재날짜 계산
def get_curday():
    return date.today().strftime("%Y-%m-%d")

# Timestamp 객체를 문자열로 변환하는 함수
def timestamp_to_str(ts):
    if isinstance(ts, Timestamp):
        return ts.strftime('%Y-%m-%d')
    return ts

# 날짜 데이터가 들어있는 리스트를 변환
def convert_data_for_json(data):
    dates_converted = [timestamp_to_str(date) for date in data.index]
    values = data.values.tolist()
    return dates_converted, values

# 차트를 Base64 인코딩된 문자열로 변환하는 기본 함수
def get_chart_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)  # 차트 닫기
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# plotly figure를 이미지로 변환하고 Base64로 인코딩
def get_chart_base64_plotly(fig):
    img_bytes = fig.to_image(format="png")
    return base64.b64encode(img_bytes).decode('utf-8')

# json으로 저장시키기
def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
# 날짜로부터 쿼터계산
def get_quarter_from_date(curday):
    date_obj = datetime.strptime(curday, "%Y-%m-%d")
    year = date_obj.year
    quarter = (date_obj.month - 1) // 3 + 1
    return f"FY{quarter}Q{year}"

# 성장률 계산 함수
def calculate_growth(actual, previous):
    if actual is not None and previous is not None and previous != 0:
        return (actual - previous) / previous * 100
    return "-"

# Beat/Miss 비율 계산 함수
def calculate_beat_miss_ratio(actual, estimate):
    if actual is not None and estimate is not None:
        return "Beat" if actual > estimate else "Miss"
    return "-"

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
    
# 데이터를 JSON 파일로 저장 (종목코드 save에서 사용)
def save_data_to_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f)
        
# 데이터를 JSON 파일로 로드 (종목코드 read에서 사용)
def read_data_from_file(filename):
    with open(filename, 'r') as f:
        return json.load(f)        

# 천단위 이상 숫자에 콤마 붙여주는 함수    
def format_number_with_comma(number):
    # 숫자와 문자를 분리
    if isinstance(number, str) and '%' in number:
        num_part, percent_sign = number.rstrip('%'), '%'
    else:
        num_part, percent_sign = str(number), ''
    try:
        num_part_float = float(num_part)
        formatted_num = f"{num_part_float:,.2f}"
    except ValueError:
        return number
    if num_part_float >= 1000:
        return formatted_num + percent_sign
    else:
        return str(number)    
    
# 1년전 날짜 구하기    
def get_one_year_before(end_date):
    return end_date - timedelta(days=365)

# Nan 또는 None 값 체크 함수
def is_valid(value):
    if value is None:
        return False
    if isinstance(value, (float, int)) and math.isnan(value):
        return False
    return True

# Convert NaN to None 
def handle_nan(obj):
    if isinstance(obj, float) and np.isnan(obj):
        return None
    return obj