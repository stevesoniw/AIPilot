#Basic 함수
from datetime import datetime 
import matplotlib
matplotlib.use('Agg')

########## personal made 파일 ##########
#라우터
from frControllerAI import frControllerAI
from frControllerETC import frControllerETC
from dmController import dmController
from ragController import ragController
from smController import smController
#######################################
#FAST API 관련
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
#######################################
#Environment 관련
from datetime import datetime
import logging
import asyncpg


app = FastAPI()
app.include_router(frControllerAI)
app.include_router(frControllerETC)
app.include_router(dmController)
app.include_router(ragController)
app.include_router(smController)
logging.basicConfig(level=logging.DEBUG)

##############################################       접속 카운트      #################################################

async def get_database_connection():
    return await asyncpg.connect(user='postgres', password='mirae01!@', database='your_database', host='127.0.0.1')

@app.middleware("http")
async def count_visitors(request: Request, call_next):
    # 데이터베이스 연결
    conn = await get_database_connection()
    try:
        # 오늘 날짜에 대한 방문자 수를 증가
        await conn.execute('''
            INSERT INTO visitors (date, count) VALUES (CURRENT_DATE, 1)
            ON CONFLICT (date) DO UPDATE SET count = visitors.count + 1;
        ''')
        response = await call_next(request)
        return response
    finally:
        await conn.close()

@app.get("/get-visitors")
async def get_visitors():
    conn = await get_database_connection()
    try:
        count = await conn.fetchval('SELECT count FROM visitors WHERE date = CURRENT_DATE;')
        return {"visitors_today": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()
                

##############################################          공통          ################################################
# FastAPI에서 정적 파일과 템플릿을 제공하기 위한 설정
templates = Jinja2Templates(directory="mainHtml")
app.mount("/static", StaticFiles(directory="mainHtml"), name="static")

# batch 폴더를 정적 파일로 제공하는 설정 추가
app.mount("/batch", StaticFiles(directory="batch"), name="batch")

##############################################          MAIN  설정        ################################################
# 루트 경로에 대한 GET 요청 처리
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 초기 페이지 렌더링. 
    date = datetime.now().strftime("%Y-%m-%d")
    summary_content = f"<p></p>"
    try:
        # 서버 사이드에서 특정 div에 들어갈 HTML 생성 로직
        file_path = f"mainHtml/main_summary/summary_{date}.html"
        with open(file_path, "r", encoding="utf-8") as file:
            summary_content = file.read()
    except FileNotFoundError:
        # 파일이 없을 경우 그냥 show 만 안함. 
        pass
    return templates.TemplateResponse("aiMain.html", {"request": request, "summary_content": summary_content})

@app.get("/aiReal", response_class=HTMLResponse)
async def frStockInfo(request: Request):
    # frStockInfo.html에 필요한 데이터를 여기에서 처리
    data = {"request": request}
    return templates.TemplateResponse("aiReal.html", data)
