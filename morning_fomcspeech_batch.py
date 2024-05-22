# Util 함수들
import asyncio
import requests
import logging
import json
from datetime import datetime
from bs4 import BeautifulSoup
import multiprocessing
import os
from fastapi import HTTPException
import urllib.parse
#금융관련 or 상용 APIs
from openai import OpenAI
from serpapi import GoogleSearch
#private made 파일
import config
import utilTool
#Langchain 관련
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document as Doc

# API KEY 설정
client = OpenAI(api_key = config.OPENAI_API_KEY)
API_KEYS = {
    "huggingface": config.HUGGINGFACE_API_KEY,
    "serpapi": config.SERPAPI_API_KEY
}
BASE_PATH = "batch/fomc/sentiment/"
logging.basicConfig(level=logging.DEBUG)

########################################################################################################################
#@@ 기능정의 : Fomc Sentiment 분석에서 timeline 스피치와 sentiment score를 미리 파일로 저장해놓는 배치 by son (24.05.05)
#@@ Logic   : 1. fomc 발표 데이터 전체 스크래핑해오고, 선택 멤버별로 데이터필터 할 수 있는 함수 생성. 
#@@              → 파일명 : 전체데이터는 batch/fomc/all/speech_all_{todaydate}.json 로 따로 저장.(요약 메인탭에서 불러오기용)
#@@           2. 보드멤버 6명에 대해 순차적으로 speech 처리 및 파일저장 
#@@           3. 나머지 멤버들은 로이터 기사 fetch 해오기 by 구글검색
#@@           4. 나머지 멤버들 데이터도 타임라인을 json 형식으로 만들어서 파일저장 
#@@           5. 위 json 파일 데이터를 한글 버전으로 하나씩 더 생성하여 저장 (클라에서 영/한 전환시 쓸것)
#@@           6. 전체 멤버들을 순차적으로 돌면서 센티멘트 분석 (speech 데이터를 허깅페이스 모듈에 던짐) 하여 다시 멤버별 파일저장         
#@@         ** 폴더명 : batch/fomc/sentiment  || 파일명 :  senti_timeline_이름_날짜.json , senti_timeline_kor_이름_날짜.json
#@@         ** 폴더명 : batch/fomc/sentiment  || 파일명 :  senti_score_이름_날짜.json 
########################################################################################################################
 
#FOMC 발표 전체 데이터 가져오기 
def scrape_speeches(url):
    """
    URL 입력했을 때 최근 FOMC 스피치 리스트를 가져오는 함수
    """
    try: 
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        eventlist_div = soup.find('div', class_='row eventlist')
        desired_section = eventlist_div.find('div', class_='col-xs-12 col-sm-8 col-md-8')

        speeches = []
        for speech in desired_section.find_all('div', class_='row'):
            date = speech.find('time').text
            link = 'https://www.federalreserve.gov' + speech.find('div', class_='col-xs-9 col-md-10 eventlist__event').find('a', href=True)['href']
            title = speech.find('em').text
            author = speech.find('p', class_='news__speaker').text

            speeches.append({'date': date, 'link': link, 'title': title, 'author': author})

        return speeches
    except Exception as e:
        logging.error(f"Failed to scrape speeches: {e}")
        return []
    
async def get_fr_social_data():
    scraped_data_2024 = scrape_speeches("https://www.federalreserve.gov/newsevents/speech/2024-speeches.htm")
    scraped_data_2023 = scrape_speeches("https://www.federalreserve.gov/newsevents/speech/2023-speeches.htm")
    scraped_data = scraped_data_2024 + scraped_data_2023
    
    data_to_store = {"data": scraped_data}
    
    logging.info("======GETTING SOCIAL DATA =======")
    todaydate = datetime.now().strftime("%Y%m%d")
    file_name = f"batch/fomc/all/speech_all_{todaydate}.json"
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(data_to_store, file, ensure_ascii=False, indent=4)    
    #print(scraped_data)
    return data_to_store

async def filter_speeches_by_author(last_name, data):
    #data = await get_fr_social_data()
    filtered_list = []
    print(last_name)
    for item in data['data']:
        item_last_name = item['author'].split(' ')[-1]  
        
        if last_name.lower() == item_last_name.lower():
            filtered_list.append(item)

    #print("**********filtered_list**********")
    #print(filtered_list)
    return filtered_list


# 모델과 유틸리티 함수 정의

def fetch_reuters_articles(person):
    """특정 인물의 로이터 기사를 가져오는 함수"""
    params = {
        #"engine": "google",
        #"engine": "google_news",
        "tbm": "nws",
        "q": f"{person} Reuters",
        "api_key": API_KEYS['serpapi'],
        "num": 20
    }
    
    try:
        search = GoogleSearch(params)
        #search_result  = serpapi.search(params)
        #results = search.get_dict()
        results = search.get_dict()
        #news_results = search ["news_results"]        
        news_results = results.get("news_results", [])

        # print(news_results)
        
        # 출처가 로이터 인것만 필터링
        reuters_articles = [article for article in news_results if article['source'] == 'Reuters']
        
        # 타이틀에 사람 이름이 들어간 것만 필터링
        filtered_articles = [article for article in reuters_articles if person.split()[-1].lower() in article['title'].lower()]
        
        # 날짜 중복인 것들 중에 중복 제거
        encountered_dates = set()
        final_articles = []
        
        for article in filtered_articles:
            formatted_date = utilTool.parse_date(article['date'])    #상대적인 날짜 있는 경우 절대날짜로 변환해주기
            if formatted_date and formatted_date not in encountered_dates:
                article['date'] = formatted_date
                final_articles.append(article)
                encountered_dates.add(formatted_date)
                
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        print(final_articles)
        return final_articles
    except Exception as e: 
        raise HTTPException(status_code=400, detail=str(e)) 

def query_huggingface_api(inputs, is_speech):
    API_URL = "https://api-inference.huggingface.co/models/gtfintechlab/FOMC-RoBERTa"
    headers = {"Authorization": f"Bearer {API_KEYS['huggingface']}"}
    
    payload = {"inputs": inputs}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to get sentiment data: {response.text}")
        return None

def scrape_speech_content(url):
    """
    URL 입력했을 때 URL 안에 있는 스피치 텍스트를 가져오는 함수
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    desired_section = soup.find('div', class_='col-xs-12 col-sm-8 col-md-8')
    
    ### 비디오 내용 제거
    unwanted_div = desired_section.find('div', class_='col-xs-12 col-md-7 pull-right')
    if unwanted_div:
        unwanted_div.decompose()
    ## 엔딩을 가리키는 hr태그 찾기
    hr_tag = desired_section.find('hr')
    # Extract the content before the <hr> tag
    if hr_tag:
        previous_content = hr_tag.find_previous_siblings()
        result_str = ""
        for tag in reversed(previous_content):
            # print(tag)
            result_str += tag.text + "\n\n"
    else:
        result_str = desired_section.text.strip()
    
    return result_str    

def extract_main_sentence(url):
    """
    url에 대해 url 텍스트 전체를 크롤링하고 텍스트 중 주요 문장 추출하는 함수
    """
    text = scrape_speech_content(url)
    prompt_template = """
    You are an economist determining dovish/hawkish orientation from FOMC members' speeches.
    You will be given a speech from a FOMC member. 
    Return the main sentence from the speech that shows author's orientation. 
    If the speech does not contain such sentence, return None.
    
    The output should just be the sentence(s). Do not include other explanations.
        <Example>
        "There is no rush in cutting interest rates."

    Speech:
    "{text}"

    Answer: """
    prompt = PromptTemplate.from_template(prompt_template)

    # Define LLM chain
    llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo", streaming=True,
                     api_key=config.OPENAI_API_KEY)
    llm_chain = LLMChain(llm=llm, prompt=prompt)

    # Define StuffDocumentsChain
    stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="text", verbose=True)
        
    docs = Doc(page_content=text)
    # #     # # result1 = stuff_chain.invoke(docs)['output_text']
    # #     # # print(stuff_chain.invoke(docs))
    # #     # # # print(stuff_chain.run(docs))
    # #     # # print(type(docs))
    return stuff_chain.run([docs])
                           

async def get_sentiment_data(speeches, is_speech):
    final_results = []
    for speech in speeches:
        content_to_analyze = speech['result'] if is_speech else speech['title']
        sentiment_result = query_huggingface_api(content_to_analyze, is_speech)

        if sentiment_result:
            final_results.append({
                "date": speech["date"],
                "scores": sentiment_result,
                "result": content_to_analyze
            })

    logging.info(f"Sentiment results: {final_results}")
    return final_results


async def get_timeline_data(filtered_list):
    speeches = filtered_list
    if len(speeches) > 15:
        speeches = speeches[:15]  # 15개로 제한

    with multiprocessing.Pool(processes=10) as pool:
        # 주요 문장 뽑기 병렬 처리
        results = [pool.apply_async(extract_main_sentence, (speech["link"],)) for speech in speeches]

        final_results = []
        for speech, result in zip(speeches, results):
            extracted_result = result.get()  # 결과 받기
            if extracted_result is None or extracted_result == "None":  # 결과가 None인 경우 간지나게 바꿈
                extracted_result = "No significant remarks were made."
            final_results.append({"date": speech["date"], "title": speech["title"], "result": extracted_result})

        print("Final Results:", final_results)

    return final_results

# 번역 시키기 함수
async def translate_timeline_data(data):
    # 데이터를 한국어로 번역하는 함수
    SYSTEM_PROMPT = (
        "You are a highly skilled translator fluent in both English and Korean. "
        "Translate the following json data from English to Korean, "
        "keeping any specific terms related to the US stock market or company names in English."
        "You need to translate only the contents of title and result into Korean. Do not translate the keys or property names of the JSON data. "
        "The format of the JSON must not be changed at all. (Never attach ```json or ``` signs before or after. "
        "Make sure 'Key-value' pairs in JSON are enclosed in double quotation marks. "
        "Ensure that all double quotation marks within the translated content are properly escaped with a backslash (\\) before each double quotation mark.) "
        "Provide only the correctly formatted JSON data as your response."
    )
    pre_prompt = "Do not provide any other response besides the JSON format. Never attach ```json or ``` signs before or after. Translate only the contents of title and result into Korean, ensuring that 'Key-value pairs' in JSON are enclosed in double quotation marks and that all double quotation marks within the translated content are properly escaped with a backslash (\\) before each double quotation mark. This is JSON data: "
    prompt = f"{pre_prompt}\n\n{data}"
    try:
        completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred during translate_timeline_data: %s", e)
        return None    

# 메인 배치 처리 로직
async def process_member(member, data, is_board_member=True):
    """멤버 데이터 처리 및 파일 저장"""
    today = datetime.now().strftime("%Y%m%d")
    last_name= utilTool.get_last_name(member)
    file_path = os.path.join(BASE_PATH, f"senti_timeline_{last_name}_{today}.json")
    file_score_path = os.path.join(BASE_PATH, f"senti_score_{last_name}_{today}.json")
    file_kor_path = os.path.join(BASE_PATH, f"senti_timeline_kor_{last_name}_{today}.json")
 
    if is_board_member:
        # 연설 데이터 수집 및 감정 분석
        filtered_list = await filter_speeches_by_author(last_name, data)
        timeline_data  = await get_timeline_data(filtered_list)
        sentiment_data = await get_sentiment_data(timeline_data, True)
    else:
        # 기사 데이터 수집 및 감정 분석
        timeline_data  = fetch_reuters_articles(member)
        sentiment_data = await get_sentiment_data(timeline_data, False)

    # 결과 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, ensure_ascii=False, indent=4)
    with open(file_score_path, 'w', encoding='utf-8') as f:
        json.dump(sentiment_data, f, ensure_ascii=False, indent=4)

    translated_data = await translate_timeline_data(timeline_data)
    if translated_data:
        with open(file_kor_path, 'w', encoding='utf-8') as f:
            f.write(translated_data)  
            logging.info(f"Translated data saved to {file_kor_path}")
    else:
        logging.error(f"Failed to translate data for {member}")

    logging.info(f"Processed data for {member} saved to {file_path} and {file_score_path}")

async def main():
    
    initial_data = await get_fr_social_data()
        
    members = {
        'board': ['Jerome Powell', 'Philip Jefferson', 'Michael Barr', 'Michelle Bowman', 'Lisa Cook', 'Adriana Kugler', 'Christopher Waller'],
        'non_board': ['John Williams', 'Thomas Barkin', 'Raphael Bostic', 'Mary Daly', 'Loretta Mester']
    }

    tasks = []
    for member in members['board']:
        tasks.append(process_member(member, initial_data, True))
    for member in members['non_board']:
        tasks.append(process_member(member, initial_data, False))
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
    #fetch_reuters_articles("Barkin")
