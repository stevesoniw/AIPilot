from fastapi import FastAPI, File, UploadFile, HTTPException, APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.requests import Request  
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import tempfile
import logging
# 개인 클래스
from rag_openai import ChatPDF 
from multiRAG import multiRAG

# 기본 함수들은 다 rag_openai(*디지털리서치 파일업로드), multiRAG(*AI해외주식 talk) 파일에 정의함 

logging.basicConfig(level=logging.DEBUG)
router = APIRouter()
# FastAPI로 ChatPDF 인스턴스 초기화
assistant = ChatPDF()
askMulti = multiRAG()

############################################[3RD GNB] [1ST LNB] 리서치 RAG 테스트쪽 ############################################
@router.post("/upload-file/")
async def create_upload_file(file: UploadFile = File(...)):
    try:
        # 파일 확장자 확인
        file_extension = file.filename.split('.')[-1].lower()
        file_name_itself = '.'.join(file.filename.split('.')[:-1])
        if file_extension not in ['pdf', 'docx']:
            return {"error": "Unsupported file type."}

        with tempfile.NamedTemporaryFile(delete=False, suffix="." + file_extension) as temp_file:
            temp_file.write(await file.read())
            # 파일 타입에 따라 ingest 함수 호출
            await assistant.ingest(file_path=temp_file.name, file_type=file_extension)
            await assistant.ingest(file_path=temp_file.name, file_type=file_extension, file_name_itself=file_name_itself)
        return {"filename": file.filename}
    finally:
        os.remove(temp_file.name)

class Message(BaseModel):
    message: str
@router.post("/process-message/")
async def process_message(message_body: Message):
    message = message_body.message
    if not message or len(message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty message")
    
    response_message = await assistant.ask(message.strip())
    return {"message": response_message}

############################################[3RD GNB] [2ND LNB] AI 투자비서 테스트쪽 ############################################
@router.post("/rag/ai-sec-upload/")
async def handle_ai_sec_file(
    file: UploadFile = File(...), 
    employeeId: Optional[str] = Form(None) # 사번을 Form 데이터로 받음
):
    try:
        # 파일 확장자 확인
        file_extension = file.filename.split('.')[-1].lower()
        file_name_itself = '.'.join(file.filename.split('.')[:-1])
        if file_extension not in ['pdf', 'docx']:
            return {"error": "Unsupported file type."}

        with tempfile.NamedTemporaryFile(delete=False, suffix="." + file_extension) as temp_file:
            temp_file.write(await file.read())
            # 파일 타입과 사번에 따라 ingest 함수 호출
            await assistant.ai_sec_file_control(
                file_path=temp_file.name, 
                file_type=file_extension, 
                file_name_itself=file_name_itself, 
                employeeId=employeeId  # 사번도 매개변수로 전달
            )
        return {"filename": file.filename, "employeeId": employeeId}
    finally:
        if temp_file:
            os.remove(temp_file.name)

# AI 투자비서 [사번에 딸린 DB 조회하기]
@router.post("/rag/ai-sec-viewmydb/")
async def handle_ai_sec_viewmydb(request: Request):
    try:
        data = await request.json()  
        logging.info(f"Data received: {data}")
        employeeId = data.get('employeeId')
        if not employeeId:
            raise ValueError("No employeeId received")

        response_message = await assistant.ai_sec_viewmydb(employeeId)
        return {"message": "Success", "result": response_message}

    except Exception as e:
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
# AI 투자비서 [사번에 딸린 DB 클리어하기] 
@router.post("/rag/ai-sec-cleardb/")
async def handle_ai_sec_clearmydb(request: Request):
    try:
        data = await request.json()  
        logging.info(f"Data received: {data}")
        employeeId = data.get('employeeId')
        if not employeeId:
            raise ValueError("No employeeId received")

        response_message = await assistant.ai_sec_clearmydb(employeeId)
        return {"message": "Success", "result": response_message}

    except Exception as e:
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
        
    
# AI 투자비서 [질문에 대해 답변하기]
@router.post("/rag/ai-sec-talk/")
async def handle_ai_sec_talk(request: Request):
    try:
        data = await request.json()  
        logging.info(f"Data received: {data}")
        message = data.get('message') 
        employeeId = data.get('employeeId')
        if not message:
            raise ValueError("No message received")

        response_message = await assistant.ai_sec_talk(message, employeeId)
        return {"message": "Success", "result": response_message}

    except Exception as e:
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


#################################### [1ST GNB] AI가 말해주는 해외주식정보 채팅영역 #####################################

# AI가 말해주는 해외주식정보 [1.사용자가 조회한 주식정보 데이터 저장용]
@router.post("/rag/handle-ai-query/")
async def handle_ai_query(request: Request):
    print("Request handling started.")
    try:
        client_ip = request.client.host
        print("****************************************")
        print("Client IP:", client_ip)

        json_body = await request.json()
        print("JSON body loaded successfully.")
        
        markdown_data = json_body.get("markdownData")
        if not markdown_data:
            raise ValueError("No markdown data received or data is empty")
        print("Markdown data received:", markdown_data)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        markdown_dir = os.path.join(current_dir, 'markdown')
        os.makedirs(markdown_dir, exist_ok=True)        

        markdown_file_path = os.path.join(markdown_dir, f"{client_ip}_markdown.md")
        with open(markdown_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write(markdown_data)
        print("Markdown data saved to:", markdown_file_path)

        try:
            print("Calling foreignStockLoader with:", markdown_file_path, client_ip)
            response_message = await askMulti.foreignStockLoader(markdown_file_path, client_ip)
            print("Response from foreignStockLoader:", response_message)
        except Exception as e:
            print("Error calling foreignStockLoader:", e)
            raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        print("Unexpected error:", e)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    return JSONResponse(content={"message": "Success", "result": response_message})

# AI가 말해주는 해외주식정보 [2. 탐색원하는 WEB URL 데이터 저장시키기]
class WebURL(BaseModel):
    url: str
def get_client_ip(request: Request):
    return request.client.host    
@router.post("/rag/handle-webbased-query/")
async def handle_webbased_query(web_url: WebURL, client_ip: str = Depends(get_client_ip)):
    try:
        url = web_url.url
        logging.info(f"url received: {url}")

        response_message = await askMulti.webUrlLoader(url, client_ip)
        return {"message": "Success", "result": response_message}

    except ValueError as ve:
        logging.exception("Validation error")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.exception("An unexpected error occurred")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")

# AI가 말해주는 해외주식정보 [질문에 대해 답변하기]
@router.post("/rag/handle-ai-answer/")
async def handle_ai_answer(request: Request):
    try:
        client_ip = request.client.host        
        data = await request.json()  
        logging.info(f"Data received: {data}")
        message = data.get('message') 
        if not message:
            raise ValueError("No message received")

        response_message = await askMulti.askRetriver(message,client_ip)
        return {"message": "Success", "result": response_message}

    except Exception as e:
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# AI가 말해주는 해외주식정보 [일반적인 GPT4 질문 답변]
@router.post("/rag/handle-gpt4-talk/")
async def handle_gpt4_talk(request: Request):
    try:
        data = await request.json()  
        message = data.get('message') 
        if not message:
            raise ValueError("No message received")

        response_message = await askMulti.askGPT4(message)
        return {"message": "Success", "result": response_message}

    except Exception as e:
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")   
    
# AI가 말해주는 해외주식정보 [구글검색(serperAPI)하여 답변]
@router.post("/rag/handle-google-talk/")
async def handle_gpt4_talk(request: Request):
    try:
        data = await request.json()  
        message = data.get('message') 
        if not message:
            raise ValueError("No message received")

        response_message = await askMulti.serperAPI(message)
        return {"message": "Success", "result": response_message}

    except Exception as e:
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")       

# AI가 말해주는 해외주식정보 [해외 종목뉴스 원문 1개 분석]
@router.post("/rag/handle-analyze-webnews/")
async def handle_analyze_webnews(web_url: WebURL):
    try:
        url = web_url.url
        logging.info(f"url received: {url}")

        response_message = await askMulti.webNewsAnalyzer(url)
        return {"message": "Success", "result": response_message}

    except ValueError as ve:
        logging.exception("Validation error")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.exception("An unexpected error occurred")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")    
         