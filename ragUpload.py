from fastapi import FastAPI, File, UploadFile, HTTPException, APIRouter
from fastapi.responses import HTMLResponse
from rag_openai import ChatPDF
from typing import List
import os
import tempfile

# ChatPDF 클래스 및 기타 필요한 모듈을 여기에 임포트하세요
# from rag_openai import ChatPDF

router = APIRouter()
# FastAPI로 ChatPDF 인스턴스 초기화
assistant = ChatPDF()

@router.post("/upload-file/")
async def create_upload_file(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(await file.read())
            assistant.ingest(temp_file.name)
        return {"filename": file.filename}
    finally:
        os.remove(temp_file.name)

@router.post("/process-message/")
async def process_message(message: str):
    if not message or len(message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty message")

    response_message = assistant.ask(message.strip())
    return {"message": response_message}

