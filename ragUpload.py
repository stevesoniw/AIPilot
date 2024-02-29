from fastapi import FastAPI, File, UploadFile, HTTPException, APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from rag_openai import ChatPDF
from typing import List
import os
import tempfile

# 기본 함수들은 다 rag_openai 파일에 정의함 

router = APIRouter()
# FastAPI로 ChatPDF 인스턴스 초기화
assistant = ChatPDF()

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

