from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import matplotlib.pyplot as plt
from pandas import Timestamp
from io import BytesIO
import math
import numpy as np
import base64
import json 
import logging
import httpx
from fastapi.responses import StreamingResponse
from openai import OpenAI
from groq import Groq
import config


# API KEY 설정

clientstream = OpenAI(api_key = config.OPENAI_API_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
groq_clientstream = Groq(api_key=config.GROQ_CLOUD_API_KEY)
groq_client = Groq(api_key=config.GROQ_CLOUD_API_KEY)

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
            #model="gpt-4-0125-preview",
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
    
#GPT4 스트리밍방식    
async def gpt4_news_sum_stream(newsData, SYSTEM_PROMPT):
    try:
        prompt = """다음이 system 이 이야기한 뉴스 데이터야. system prompt가 말한대로 실행해줘. 단 답변을 꼭 한국어로 해줘. 너의 전망에 대해서는 <span style="color:#f58220"> 로 표시해줘. 대답은 항상 '-입니다, -습니다' 체로 존댓말로 해. 답변은 <p> 태그 안에 넣어서 줘. 예시: <p> 전체답변 </p>
        뉴스 데이터 : """ + str(newsData)        
        completion = clientstream.chat.completions.create(
            #model="gpt-4-0125-preview",
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ],
            stream=True          
        ) 

        for chunk in completion:
            if chunk.choices[0].delta.content is not None:            
                yield chunk.choices[0].delta.content            
        
    except Exception as e:
        logging.error("An error occurred in gpt4_news_sum function: %s", str(e))
        yield None     
    
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

# GPT4 일반호출 함수
async def gpt4_request(prompt):
    try:
        completion = client.chat.completions.create(
            #model="gpt-4-0125-preview",
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
                ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in gpt4_news_sum function: %s", str(e))
        return None
    

# Lama3 API TEST 해보기
async def lama3_news_sum(newsData, SYSTEM_PROMPT):
    try:
        prompt = "다음이 system 이 이야기한 뉴스 데이터야. system prompt가 말한대로 실행해줘. 단 답변을 꼭 한국어로 해줘. korean 외의 언어로는 절대 답변하지 말고, 화면 가독성이 좋도록 줄바꿈도 해서 답변해줘. 뉴스 데이터 : " + str(newsData)
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ],
            model="llama3-8b-8192"
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in lama3_news_sum function: %s", str(e))
        return None    

async def mixtral_news_sum(newsData, SYSTEM_PROMPT):
    try:
        prompt = "다음이 system 이 이야기한 뉴스 데이터야. system prompt가 말한대로 실행해줘. 단 답변을 꼭 한국어로 해줘. korean 외의 언어로는 절대 답변하지 말고, 화면 가독성이 좋도록 줄바꿈도 해서 답변해줘. 뉴스 데이터 : " + str(newsData)
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ],
            model="mixtral-8x7b-32768",
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in lama3_news_sum function: %s", str(e))
        return None    

async def mixtral_news_sum_stream(newsData, SYSTEM_PROMPT):
    try:
        prompt = "다음이 system 이 이야기한 뉴스 데이터야. system prompt가 말한대로 실행해줘. 단 답변을 꼭 한국어로 해줘. korean 외의 언어로는 절대 답변하지 말고, 화면 가독성이 좋도록 줄바꿈도 해서 답변해줘. 뉴스 데이터 : " + str(newsData)
        completion = groq_clientstream.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ],
            model="mixtral-8x7b-32768",
            stream= True
        )

        for chunk in completion:
            if chunk.choices[0].delta.content is not None:            
                yield chunk.choices[0].delta.content                           
        
    except Exception as e:
        logging.error("An error occurred in lama3_news_sum function: %s", str(e))
        yield None
        
# 공백기준으로 이름 뒤에를 리턴  
def get_last_name(full_name):
    parts = full_name.split()
    # 마지막 부분(성)을 반환
    return parts[-1] if parts else ''

# 날짜 문자열 변환 함수 
def parse_date(date_str):
    """
    날짜 문자열을 받아 절대 날짜로 변환합니다.
    예: "3 weeks ago", "2 days ago", "1 month ago" -> 2024/2/16 형식으로 변환
    """
    now = datetime.now()
    relative_match = re.match(r"(\d+) (week|month|day)s? ago", date_str)
    
    if relative_match:
        quantity = int(relative_match.group(1))
        time_unit = relative_match.group(2)
        
        if time_unit == 'day':
            now -= relativedelta(days=quantity)
        elif time_unit == 'week':
            now -= relativedelta(weeks=quantity)
        elif time_unit == 'month':
            now -= relativedelta(months=quantity)
            
        return now.strftime("%Y/%m/%d")
    else:
        try:
            # 이미 정확한 날짜로 주어진 경우
            exact_date = datetime.strptime(date_str, '%b %d, %Y')
            return exact_date.strftime("%Y/%m/%d")
        except ValueError:
            # 날짜 형식을 인식할 수 없는 경우
            return None
   