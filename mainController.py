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
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.include_router(frControllerAI)
app.include_router(frControllerETC)
app.include_router(dmController)
app.include_router(ragController)
app.include_router(smController)
logging.basicConfig(level=logging.DEBUG)

##############################################          공통          ################################################
# FastAPI에서 정적 파일과 템플릿을 제공하기 위한 설정
templates = Jinja2Templates(directory="mainHtml")
app.mount("/static", StaticFiles(directory="mainHtml"), name="static")

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
