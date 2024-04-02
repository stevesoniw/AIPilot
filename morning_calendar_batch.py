# Util 함수들
import asyncio
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse, ParserError
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Query, Form, HTTPException, Request, File, UploadFile
import json
import httpx
import re
#금융관련 APIs
from openai import OpenAI
import finnhub
#private made 파일
import config
import utilTool

# API KEY 설정
client = OpenAI(api_key = config.OPENAI_API_KEY)
rapidAPI = config.RAPID_API_KEY
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
logging.basicConfig(level=logging.DEBUG)

########################################################################################################################
#@@ 기능정의 : rapid API 와 finnhub calendar api 를 활용하여 미리 캘린더 데이터를 생성해놓는 배치파일 by son (24.03.31)
#@@ Logic   : 1. rapid API로 economic calendar 데이터를 얻어옴
#@@           2. gpt 를 이용하여 이에 대한 한국어 번역 데이터도 따로 얻어옴
#@@           3. gpt 를 이용하여 이번 달 주요 내용을 번역,요약시킴
#@@           4. finnhub ipo calendar API를 활용하여 ipo calendar 데이터를 얻어옴
#@@         ** → 이들을 각각 파일로 저장함
#@@         ** → 최종적으로 파일들을  frCalendar.js 에서 불러와서 aiMain.html 에 넣어준다.     
#@@         ** 파일명 :: eco_calendar_eng.json, eco_calendar_kor.json, eco_calendar_aisummary.txt, ipo_calendar_eng.json
########################################################################################################################

# GPT4 에 뉴스요약을 요청하는 공통함수
async def gpt4_chart_talk(system_prompt, prompt):
    try:
        completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
                ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in gpt4_chart_talk function: %s", str(e))
        return None
                        
async def rapidapi_calendar():
    url = "https://trader-calendar.p.rapidapi.com/api/calendar"
    Start_date_calen = (datetime.strptime(utilTool.get_curday(), "%Y-%m-%d") - timedelta(days=365)).strftime("%Y-%m-%d") # 최근 6개월 
    payload = { "country": "USA", "start": str(Start_date_calen)}
    headers = {
	    "content-type": "application/json",
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "trader-calendar.p.rapidapi.com"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
    return response.json()

async def get_ipo_calendar():
    try:
        # 현재 날짜를 기준으로 계산
        Start_date_calen = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")  # 현재 시점 - 100일
        End_date_calen = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")  # 현재 시점 + 90일
        recent_ipos = finnhub_client.ipo_calendar(_from=Start_date_calen, to=End_date_calen)
        base_path = Path("batch/calendar")  
        base_path.mkdir(parents=True, exist_ok=True)
        file_path = base_path / "ipo_calendar_eng.json"
        with file_path.open("w") as file:
            json.dump(recent_ipos, file, ensure_ascii=False)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
       
async def translate_calendar_data(data):
    # 데이터를 한국어로 번역하는 함수
    SYSTEM_PROMPT = (
        "You are a highly skilled translator fluent in both English and Korean. "
        "Translate the following economic calendar data from English to Korean, "
        "keeping any specific terms related to the US stock market or company names in English. Do not provide any other response besides the JSON format. If it seems like the token count will exceed the limit and cut off in the middle, ensure that the JSON data finishes without any errors by showing data only up to the previous ID and properly closing the JSON."
    )
    #다 던지면 gpt토큰 수 제한에 걸리므로 최근 일부만 번역하자
    current_date = datetime.now()
    three_months_ago = current_date - relativedelta(months=3)
    filtered_data = []
    for event in data:
        try:
            event_start = parse(event['start']).replace(tzinfo=None)
            if three_months_ago <= event_start <= current_date:
                filtered_data.append(event)
        except ParserError:
            print(f"날짜 형식 오류: {event['start']}")
    pre_prompt = "Do not provide any other response besides the JSON format. Even if the request token size is too large, don't mention it, just return the JSON data. Ensure to properly close the JSON data to prevent it from becoming unstable due to being cut off in the middle."
    prompt = f"{pre_prompt}\n\n{json.dumps(filtered_data, ensure_ascii=False)}"
    try:
        translate_result = await gpt4_chart_talk(SYSTEM_PROMPT, prompt)
        print("*******************************************")
        print(translate_result)
    except Exception as e:
        logging.error("An error occurred during summarization: %s", e)
        return None    
    return translate_result

async def summarize_this_month_calendar(data):
    # 이번 달 캘린더 데이터를 요약 정리하는 함수
    current_month = datetime.now().month
    current_year = datetime.now().year
    filtered_data = []
    # 날짜 파싱 시 ParserError 처리
    for event in data:
        try:
            if parse(event['start']).month == current_month and parse(event['start']).year == current_year:
                filtered_data.append(event)
        except ParserError as e:
            logging.error(f"날짜 파싱 오류: {e} - 이벤트 '{event['start']}' 는 무시됩니다.")
            continue
        
    SYSTEM_PROMPT = "You are an expert in summarizing economic data. To make the data readable on the screen, add appropriate <br> tags or color tags."
    prompt = (
        "You are an expert in summarizing economic data. Please provide a concise summary in Korean "
        "of the following key economic events for this month, highlighting their potential impact on the market. "
        "Keep specific US stock market or company names in English.\n\n"
        f"{json.dumps(filtered_data, ensure_ascii=False)}"
    )
    try:
        summary_result = await gpt4_chart_talk(SYSTEM_PROMPT, prompt)
    except Exception as e:
        logging.error("요약 작업 중 오류 발생: %s", e)
        return None
    return summary_result

async def get_financial_stockNews(ticker: str):
    try:
        #현재 날짜를 기준으로 Finnhub에서 데이터 조회 (일단 데이터없는 종목들이 많아서 3개월치 가져온다)
        Start_date_calen = (datetime.strptime(utilTool.get_curday(), "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d") # 현재 시점 - 3개월 
        End_date_calen = utilTool.get_curday()     
        recent_news = finnhub_client.company_news(ticker, _from=Start_date_calen, to=End_date_calen)
        return recent_news
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
async def main():
    # 데이터 가져오기
    base_path = Path("batch/calendar")
    base_path.mkdir(parents=True, exist_ok=True)    
    calendar_data = await rapidapi_calendar()
    ipo_calendar = await get_ipo_calendar() 
    
    # 영어 데이터 저장
    eng_path = base_path / "eco_calendar_eng.json"
    with eng_path.open("w") as file:
        json.dump(calendar_data, file, ensure_ascii=False)
    
    # 데이터를 한국어로 번역. 생성된 json이 에러도 많고 번역 토큰도 많이 필요. 
    # 일단 막아놓고, 영문json 을 수기로 번역해서 사용한다. 
    '''try:
        kor_data = await translate_calendar_data(calendar_data)

        kor_data = kor_data.strip("`json\n```")
        processed_data = kor_data.replace('\\"', '"')
     
        print(processed_data)
        kor_path = f"{base_path}/eco_calendar_kor.json"
        with open(kor_path, "w", encoding="utf-8") as file:
            file.write(processed_data)
    except Exception as e:
        logging.error("파일 저장 중 오류 발생: %s", e)'''
    
    # 이번 달 데이터 요약
    try:
        summary = await summarize_this_month_calendar(calendar_data)  
        print("**********")
        print(summary)
        # 데이터 가공: "-"를 "<br>"로, "**내용**"을 스타일이 적용된 "<b style='color: darkgray;'>내용</b>"으로
        formatted_summary = summary.replace("-", "<br>")
        formatted_summary = re.sub(r"\*\*(.*?)\*\*", r"★<b style='color:#181818;'>\1</b> ", summary)
        formatted_summary = re.sub(r"(\d+)\.", r"<br>\1.", formatted_summary)
        summary_path = base_path / "eco_calendar_aisummary.html" 
        with summary_path.open("w", encoding="utf-8") as file:
            file.write(formatted_summary)
    except Exception as e:
        logging.error("요약 파일 저장 중 오류 발생: %s", e)

if __name__ == "__main__":
    asyncio.run(main())