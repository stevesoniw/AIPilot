# AIPilot

# 핵심 파일 
 - newbond.py (FastAPI 환경. 현재 해당파일에 모든 로직이 존재) 
 - config.py (*openAI key 가 disable 되는 관계로 내용은 비워서 커밋함)
 - chartHtml\chart_pilot.html (클라이언트 화면) 
 - chartHtml\assets\css\chart-pilot.css (메인 css 파일)

 - 아침 배치파일 : morining_brief_batch.py (메인화면 데이터 html로 떨구는 용도)
 - RAG 관련 : ragControlTower.py = 여기서 multiRAG.py, rag_openai.py 컨트롤 함 (router형태로 chart_pilot.html과 직접 연결)
 - 나머지 .py들은 쓸데없는 파일이라 보면됨
  

# 해야할 일
  - 체계적으로 관리되도록 파일쪼개기

# Develope To Do
  [중요도 상]
  - 리서치 랭체인 구현 (+벡터DB연결)
    : Q&A 챗봇 구현 .  이때 특정 웹사잍트, FinnHub api, 구글 API,  특정 내부 PDF 를 기반으로 답변 (랭체인)
  - 뉴스, 트위터, 소셜 미디어 데이터로 화면구성 + AI요약 및 의견제시
  - AI가 말해주는 주식정보(해외) :  FINGPT 활용한 실적데이터, 한글 번역, 정량데이터 등 추가
    
  [중요도 중]
  - 연준발표 긁어와서 보여주기
    
  [중요도 하]
  - 카톡알림
  - 배치모듈개발

  
