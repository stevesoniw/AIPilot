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
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import asyncpg

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
##############################################       접속 카운트      #################################################
@asynccontextmanager
async def db_connection_manager(application: FastAPI):
    logger.debug("Attempting to connect to the database.")
    try:
        db_pool = await asyncpg.create_pool(
            host="127.0.0.1",
            port="5000",
            user="postgres",
            password="mirae01!@",  # 비밀번호 확인
            database="postgres"   # 데이터베이스 이름 확인
        )
        app.state.db_pool = db_pool
        logger.debug("Database connection established.")
        yield
    finally:
        logger.debug("Closing database connection.")
        await db_pool.close()


app = FastAPI(lifespan=db_connection_manager)

@app.middleware("http")
async def count_visitors(request: Request, call_next):
    if not hasattr(request.app.state, 'db_pool'):
        logger.error("Database pool not available in app state.")
    if request.url.path.startswith("/static/"):
        response = await call_next(request)
        return response        
    else : 
        try:
            ip_address = request.client.host  # Get client IP address
            async with request.app.state.db_pool.acquire() as conn:
                logger.debug("Database connection acquired for visitor counting.")
                await conn.execute('''
                    INSERT INTO visitors (visit_date, visitor_count, ip_address)
                    VALUES (CURRENT_DATE, 1, $1)
                    ON CONFLICT (visit_date) DO UPDATE
                    SET visitor_count = visitors.visitor_count + 1;
                ''', ip_address)  # Pass the IP address as a parameter to the SQL query
                logger.debug("Visitor count updated successfully.")
        except Exception as e:
            logger.error(f"Error updating visitor count: {e}")
    
    response = await call_next(request)
    return response

##############################################          공통          ################################################
# 라우터들 설정
app.include_router(frControllerAI)
app.include_router(frControllerETC)
app.include_router(dmController)
app.include_router(ragController)
app.include_router(smController)

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
