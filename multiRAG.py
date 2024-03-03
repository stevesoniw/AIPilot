# AI 유틸
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain_community.document_loaders.web_base import WebBaseLoader
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.messages import HumanMessage

# DB 관련
from langchain_community.vectorstores import Chroma
from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.vectorstores.utils import filter_complex_metadata
from langchain.docstore.document import Document as Doc
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains import create_retrieval_chain

# 기본 유틸
import config
import os
import uuid
from pprint import pprint

from bs4 import BeautifulSoup as Soup

class multiRAG:
    LLM_MODEL_NAME = "gpt-4-0125-preview"
    #OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"
    OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(self):
        # openAI 쪽 정의
        self.llmModel = ChatOpenAI(temperature=0.1, openai_api_key=config.OPENAI_API_KEY)
        self.embeddings = OpenAIEmbeddings(model=self.OPENAI_EMBEDDING_MODEL, openai_api_key=config.OPENAI_API_KEY)
        # text_splitter 정의 
        self.text_splitter = CharacterTextSplitter(chunk_size=1024, chunk_overlap=100, length_function=len, separator= "\n\n\n")
        self.re_text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        # 기본 prompt 정의
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant. Answer questions using only the following context. If you don't know the answer just say you don't know, don't make it up:\n\n{context}",
                ),
                ("human", "{question}"),
            ]
        )
        # Elastic Search 정리
        '''self.ES_INDEX_NAME = "research-test"
        self.ES_URL = config.ELASTIC_URL
        self.ES_USERNAME = config.ELASTIC_USER
        self.ES_PASSWORD = config.ELASTIC_PW
        self.es_client = Elasticsearch(hosts=[self.ES_URL], basic_auth=(self.ES_USERNAME, self.ES_PASSWORD))'''
        # Chroma DB 설정
        #db_client = chromadb.PersistentClient()
        #web_collection = db_client.create_collection(
        #    name="web_collection"
        #)
        self.persist_directory = './chroma_database/'
    
    # 클라에서 데이터 조회한것 저장시키기
    async def foreignStockLoader(self, file_path, user_identifier):
        loader = UnstructuredMarkdownLoader(file_path)
        data = loader.load()
        chunks = self.text_splitter.split_documents(data)
        chunks = filter_complex_metadata(chunks)

        user_persist_directory = os.path.join(self.persist_directory, user_identifier)
        os.makedirs(user_persist_directory, exist_ok=True)
        
        vectordb = Chroma.from_documents(documents=chunks, embedding=self.embeddings, persist_directory=user_persist_directory)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant. Answer questions using only the following context. If you don't know the answer just say you don't know, don't make it up:\n\n{context}",
                ),
                ("human", "{question}"),
            ]
        )      
        self.retriever = vectordb.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 3,
                "score_threshold": 0.1,
            },
        )        
        chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | prompt
                      | self.llmModel
                      | StrOutputParser()) 
        
        result = chain.invoke("네가 얻은 정보들에 대해서 요약해서 알려줘. 한국어로 답변해줘") 
        return result

    
    # URL Base로 데이터 저장하기
    async def webUrlLoader(self, url, user_identifier):
        user_persist_directory = os.path.join(self.persist_directory, user_identifier)
        os.makedirs(user_persist_directory, exist_ok=True)        
        loader = WebBaseLoader(url).load_and_split()
        main_prompt = PromptTemplate(
            template = """다음은 특정 웹사이트야. 웹사이트의 모든 내용을 체계적이고 자세하게 정리해줘
            {text}
            """,
            input_variables=['text']
        )
        combine_prompt = PromptTemplate(
            template="""다음 웹사이트 내용에 대해 간단히 설명해주고, 반드시 한국말로 답변해줘. 그리고 다음 문장을 꼭 답변 마지막에 붙여줘.'해당 사이트 내용에 대해 무엇이든 질문해보세요!']
            {text}
            """,
            input_variables=['text']
        )        
        chain_main = load_summarize_chain(self.llmModel,
                                          map_prompt=main_prompt,
                                          chain_type='map_reduce',
                                          verbose=False)
        chain_summary = load_summarize_chain(self.llmModel,
                                             map_prompt=combine_prompt,
                                             chain_type='map_reduce',
                                             verbose=False)    
            
        docs = chain_main.invoke(loader)
        texts = docs['input_documents']
        vectordb = Chroma.from_documents(documents=texts, embedding=self.embeddings, persist_directory=user_persist_directory)
        result = chain_summary.invoke(loader)
        return result

    #chat 질문에 대한 답변용          
    async def askRetriver(self, query, user_identifier):
        user_persist_directory = os.path.join(self.persist_directory, user_identifier)
        os.makedirs(user_persist_directory, exist_ok=True)          
        vectordb = Chroma(persist_directory=user_persist_directory, embedding_function=self.embeddings)
       
        self.retriever = vectordb.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 3,
                "score_threshold": 0.1,
            },
        )

        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | self.prompt
                      | self.llmModel
                      | StrOutputParser())
        
        return self.chain.invoke(query)
    
    #GPT4 와의 그냥 대화용
    async def askGPT4(self, query):
        llm = self.llmModel
        answer = llm([HumanMessage(content=query)])
        result = answer.content
        return result   
       
    # Finnhub에서 조회한 종목뉴스를 분석해서 보여주기
    async def webNewsAnalyzer(self, url):
        web_splitter = CharacterTextSplitter(chunk_size=3072, chunk_overlap=150, length_function=len)
        docs = WebBaseLoader(url).load_and_split(self.text_splitter)
        template = '''다음의 내용을 한글로 요약해줘: {text}'''
        combine_template = '''{text}

        요약의 결과는 다음의 형식으로 작성해줘. 깔끔하게 줄바꿈되어 보일수있게 반드시 html형태로 답변해줘.:
        제목: 신문기사의 제목
        주요내용: 다섯 줄로 요약된 내용
        내용: 주요내용을 불렛포인트 형식으로 작성
        AI의견 : 해당 뉴스가 관련 주식 종목에 미칠만한 영향과 향후 주시해야 하는 포인트 
        '''
        prompt = PromptTemplate(template=template, input_variables=['text'])
        combine_prompt = PromptTemplate(template=combine_template, input_variables=['text'])
        
        llm = ChatOpenAI(temperature=0, model=self.LLM_MODEL_NAME, openai_api_key=config.OPENAI_API_KEY)
        chain = load_summarize_chain(llm, 
                                map_prompt=prompt, 
                                combine_prompt=combine_prompt, 
                                chain_type='map_reduce', 
                                verbose=False)
        
        result = chain.invoke(docs)
        return result


#multiCon = multiRAG()
#data = multiCon.webUrlLoader("https://www.federalreserve.gov/newsevents/speeches.htm")
#data = multiCon.askRetriver("AMERICAN AIRES 의 섹터는 뭐야?")
#texts = "### STOCKBASIC COMPANY INFO <table class='stockBasicInfoTable'><caption>종목 기본 정보</caption><tbody><tr><td>회사 이름</td><td>AMERICAN AIRES INC</td></tr><tr><td>섹터</td><td>Technology</td></tr><tr><td>현재가</td><td>0.74905</td></tr><tr><td>50일 평균가</td><td>0.2678732 (USD)</td></tr><tr><td>52주 신고가</td><td>0.765 (USD)</td></tr><tr><td>52주 신저가</td><td>0.0473 (USD)</td></tr><tr><td>총 자산</td><td>0.02억 (USD)</td></tr><tr><td>자기자본</td><td>0.01억 (USD)</td></tr><tr><td>시가총액</td><td>0.13억 (USD)</td></tr><tr><td>발행주식 수</td><td>16660000 주</td></tr><tr><td>총 부채</td><td>0.01억 (USD)</td></tr><tr><td>영업현금흐름</td><td>-0.01억 (USD)</td></tr><tr><td>PER</td><td>-1.15</td></tr><tr><td>PBR</td><td>8.99</td></tr></tbody></table>"
#file_path = "markdown\markdown.md"
#data = multiCon.askGPT4("hello")

#print(data)

#chat_pdf_instance.test()
    # 함수 실행
#chat_pdf_instance.test_retrieve_document() 
#print(chat_pdf_instance.ask("who is the author of this document?"))
