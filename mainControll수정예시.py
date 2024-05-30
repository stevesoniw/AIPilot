# 필요한 라이브러리들
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import logging
import asyncpg
from Crypto.Cipher import AES
import base64
import hashlib

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# AES256 암호화 해제 함수
def decrypt_aes256(ciphertext: str, key: str) -> str:
    key = hashlib.sha256(key.encode()).digest()
    ciphertext = base64.b64decode(ciphertext)
    iv = ciphertext[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext[16:])
    # PKCS7 패딩 제거
    pad = plaintext[-1]
    return plaintext[:-pad].decode()

# FastAPI 앱 초기화
app = FastAPI()

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

# 라우터 설정
from frControllerAI import frControllerAI
from frControllerETC import frControllerETC
from dmController import dmController
from ragController import ragController
from smController import smController

app.include_router(frControllerAI)
app.include_router(frControllerETC)
app.include_router(dmController)
app.include_router(ragController)
app.include_router(smController)

# 정적 파일과 템플릿 설정
templates = Jinja2Templates(directory="mainHtml")
app.mount("/static", StaticFiles(directory="mainHtml"), name="static")
app.mount("/batch", StaticFiles(directory="batch"), name="batch")

@app.middleware("http")
async def count_visitors(request: Request, call_next):
    path = request.url.path.rstrip('/')
    if path == '':
        menu_name = 'root'
    elif path.startswith('/static'):
        menu_name = 'static_content'
    else:
        menu_name = path.strip('/')

    if not hasattr(request.app.state, 'db_pool'):
        logger.error("Database pool not available in app state.")
    try:
        ip_address = request.headers.get('X-Forwarded-For')
        if ip_address:
            ip_address = ip_address.split(',')[0]
        else:
            ip_address = request.client.host
        async with request.app.state.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO menu_visits (visit_date, menu_name, menu_count, ip_address)
                VALUES (CURRENT_DATE, $1, 1, $2)
                ON CONFLICT (visit_date, menu_name) DO UPDATE
                SET menu_count = menu_visits.menu_count + 1;
            ''', menu_name, ip_address)
    except Exception as e:
        logger.error(f"Error updating menu visit count: {e}")

    response = await call_next(request)
    return response

@app.post("/", response_class=HTMLResponse)
async def read_root(request: Request, dataFromITSupport: str = Form(...)):
    # AES256 키 설정 (공유된 키 사용)
    aes_key = "IT지원팀과 공유된 키값"
    
    try:
        decrypted_text = decrypt_aes256(dataFromITSupport, aes_key)
        
        if not decrypted_text.startswith("MIRAE"):
            raise HTTPException(status_code=400, detail="Invalid data. 복호화에 실패했습니다.")
        
        _, user_id, date_str = decrypted_text.split('/')  # / 로 나눠서 온다고 가정 like  "MIRAE/사번/날짜")
        today_str = datetime.now().strftime("%Y%m%d")
        
        if date_str != today_str:
            return HTMLResponse(content="<h1>Mi-global 의 링크를 통해서만 접속하실 수 있습니다.</h1>", status_code=400)
            #이건 클라에서 잘 메시지띄워주도록 html 단 수정할 필요 있음.

        # 초기 페이지 렌더링
        date = datetime.now().strftime("%Y-%m-%d")
        summary_content = "<p></p>"
        try:
            file_path = f"mainHtml/main_summary/summary_{date}.html"
            with open(file_path, "r", encoding="utf-8") as file:
                summary_content = file.read()
        except FileNotFoundError:
            pass
        
        return templates.TemplateResponse("aiMain.html", {"request": request, "summary_content": summary_content})
    except Exception as e:
        logger.error(f"Decryption or validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid request")

@app.get("/aiReal", response_class=HTMLResponse)
async def frStockInfo(request: Request):
    data = {"request": request}
    return templates.TemplateResponse("aiReal.html", data)
