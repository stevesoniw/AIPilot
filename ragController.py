from fastapi import File, UploadFile, HTTPException, APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from fastapi.requests import Request  
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from tempfile import NamedTemporaryFile
from langchain_community.document_loaders import PyPDFLoader
import os
import tempfile
import logging
from konlpy.tag import Okt
from konlpy.tag import Kkma
okt = Okt()
# 유튜브
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.formatters import PrettyPrintFormatter
# 개인 클래스
from rag_openai import ChatPDF 
from multiRAG import multiRAG
# Personal Config & Util
import config
import utilTool

# 기본 함수들은 다 rag_openai(*디지털리서치 파일업로드), multiRAG(*AI해외주식 talk) 파일에 정의함 

logging.basicConfig(level=logging.DEBUG)
ragController = APIRouter()
# FastAPI로 ChatPDF 인스턴스 초기화
assistant = ChatPDF()
askMulti = multiRAG()

############################################[메모리 클리어] ############################################
@ragController.post("/rag/clear_data")
async def clear_data():
    # Clear all data from memory
    uploaded_files_data.clear()
    uploaded_files_metadata.clear()
    return {"message": "Data cleared"}

############################################[3RD GNB] [1ST LNB] 리서치 RAG 테스트쪽 ############################################
uploaded_files_data = {} #파일 데이터 메모리 적재용
uploaded_files_metadata = []
file_id_counter = 0
class FileMetadata(BaseModel):
    file_id: int
    file_name: str
@ragController.post("/rag/prompt-pdf-upload/")
async def prompt_upload_files(files: List[UploadFile] = File(...)):
    global uploaded_files_data, uploaded_files_metadata, file_id_counter
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    
    for uploaded_file in files:
        file_data = await uploaded_file.read()
        file_id_counter += 1
        file_metadata = FileMetadata(file_id=file_id_counter, file_name=uploaded_file.filename)
        
        uploaded_files_data[file_id_counter] = {
            "file_name": uploaded_file.filename,
            "content": file_data
        }
        uploaded_files_metadata.append(file_metadata.model_dump())
        print("************************************")
        print(uploaded_files_metadata)
        print("************************************")

    return {"message": "Files upload succeeded", "files_metadata": uploaded_files_metadata}

@ragController.delete("/file/{file_id}/")
async def delete_file_data(file_id: int):
    global uploaded_files_data, uploaded_files_metadata
    file_id = int(file_id)  # Ensure file_id is an integer
    if file_id not in uploaded_files_data:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove data and metadata
    del uploaded_files_data[file_id]
    uploaded_files_metadata = [data for data in uploaded_files_metadata if data['file_id'] != file_id]

    return {"message": "File deleted successfully", "files_metadata": uploaded_files_metadata}

class PromptWithFilesRequest(BaseModel):
    prompt: str
    fileIds: List[int]
@ragController.post("/rag/answer-from-prompt/")
async def process_prompt_with_files(request: PromptWithFilesRequest):
    file_data_list = []
    for file_id in request.fileIds:
        if file_id not in uploaded_files_data:
            raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found")
        file_data_list.append(uploaded_files_data[file_id])
    
    print(file_data_list)
    return {"message": "Files fetched successfully", "file_data": file_data_list}


############################################[3RD GNB] [1ST LNB] 리서치 RAG 테스트쪽 ############################################
@ragController.post("/upload-file/")
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
@ragController.post("/process-message/")
async def process_message(message_body: Message):
    message = message_body.message
    if not message or len(message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty message")
    
    response_message = await assistant.ask(message.strip())
    return {"message": response_message}

############################################[3RD GNB] [2ND LNB] AI 투자비서 테스트쪽 ############################################
@ragController.post("/rag/ai-sec-upload/")
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
@ragController.post("/rag/ai-sec-viewmydb/")
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
@ragController.post("/rag/ai-sec-cleardb/")
async def handle_ai_sec_clearmydb(request: Request):
    try:
        data = await request.json()  
        logging.info(f"Data received: {data}")
        employeeId = data.get('employeeId')
        if not employeeId:
            raise ValueError("No employeeId received")

        response_message = await assistant.ai_sec_clearmydb(employeeId)
        print(response_message)
        return {"message": "Success", "result": response_message}

    except Exception as e:
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    
# AI 투자비서 [질문에 대해 답변하기]
@ragController.post("/rag/ai-sec-talk/")
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
@ragController.post("/rag/handle-ai-query/")
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
@ragController.post("/rag/handle-webbased-query/")
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
@ragController.post("/rag/handle-ai-answer/")
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
@ragController.post("/rag/handle-gpt4-talk/")
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
@ragController.post("/rag/handle-google-talk/")
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
@ragController.post("/rag/handle-analyze-webnews/")
async def handle_analyze_webnews(request: Request):
    try:
        body = await request.json()
        url = body['url']
        ticker = body['ticker']
        newsId = body['newsId']
        logging.info(f"URL received: {url}")

        response_message = await askMulti.webNewsAnalyzer(url)
        
        print(response_message)
        # Saving the result to a file
        try : 
            if 'text' in response_message:
                text_content = response_message['text']
                save_path = f'batch/stocknews/{ticker}/{ticker}_{newsId}.txt'
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'w', encoding='utf-8') as file:
                    file.write(text_content)
        except Exception as e :
            logging.debug("frDetailedNews file save failed")
        return {"message": "Success", "result": response_message}    
    except ValueError as ve:
        logging.exception("Validation error")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.exception("An unexpected error occurred")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")    

#띄어쓰기 해보기 (KoNlp 이용)
def spacing_okt(wrongSentence):
    tagged = okt.pos(wrongSentence)
    corrected = ""
    for i in tagged:
        if i[1] in ('Josa', 'PreEomi', 'Eomi', 'Suffix', 'Punctuation'):
            corrected += i[0]
        else:
            corrected += " "+i[0]
    if corrected[0] == " ":
        corrected = corrected[1:]
    return corrected

#한글인지 아닌지 확인하기 (KoNlp 이용)
def is_korean(text):
    kkma = Kkma()
    pos = kkma.pos(text)
    for _, tag in pos:
        if tag.startswith('N'):
            return True
    return False

class YouTubeDataRequest(BaseModel):
    video_id_or_url: str
    type: str
@ragController.post("/api/youtube_data/")
async def extract_youtube_script(request_data: YouTubeDataRequest):
    video_id_or_url = request_data.video_id_or_url
    action_type = request_data.type

    # Trim the video URL to just the ID if it's longer than expected
    if len(video_id_or_url) > 11:
        video_id_or_url = video_id_or_url[-11:]
    try:
        transcript = None
        if action_type == 'read':
            transcript = YouTubeTranscriptApi.get_transcript(video_id_or_url, languages=['en', 'ko'], preserve_formatting=True)
        elif action_type == 'translate':
            transcript = YouTubeTranscriptApi.get_transcript(video_id_or_url, languages=['en', 'ko'], preserve_formatting=True)
            if is_korean(transcript) :
                transcript = transcript.translate('en').fetch()
            else :
                transcript = transcript.translate('ko').fetch()    
            '''transcripts = YouTubeTranscriptApi.list_transcripts(video_id_or_url)
            transcript = None
            for transcript_item in transcripts:
                if transcript_item.language_code == 'ko':
                    transcript = transcript_item.translate('en').fetch()
                    break
                elif transcript_item.language_code == 'en':
                    transcript = transcript_item.translate('ko').fetch()
                    break'''
        elif action_type == 'summarize':
            transcript = YouTubeTranscriptApi.get_transcript(video_id_or_url, languages=['en', 'ko'], preserve_formatting=True)
            prompt = f"You are the best at summarizing. Please summarize the following data neatly. Summarize in the same language as requested. Do not include any content other than the summary. [Data]:\n{transcript}"
            transcript = utilTool.gpt4_request(prompt)

        if transcript:
            formatter = TextFormatter()
            text_formatted = formatter.format_transcript(transcript)
            print(text_formatted)
            #일단 한줄로 만들고, 띄어쓰기 라이브러리를 이용해서 띄어쓰기한다.
            if is_korean(text_formatted) :           
                combined_text = ' '.join(text_formatted) 
                result = spacing_okt(combined_text)
            else :
                result = text_formatted
            return JSONResponse(content={"transcript": result})
        else:
            raise ValueError("Transcript not available")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
  