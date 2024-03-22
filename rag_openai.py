# AI 유틸
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.vectorstores.utils import filter_complex_metadata
from langchain.docstore.document import Document as Doc
from langchain_elasticsearch import ElasticsearchStore
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import MessagesPlaceholder
from elasticsearch import Elasticsearch
from korean_romanizer.romanizer import Romanizer
import chromadb
# 기본 유틸
import config
import os
import uuid
from pprint import pprint
#https://research-test-ki113xk.svc.gcp-starter.pinecone.io


class ChatPDF:
    vector_store = None
    retriever = None
    chain = None
    LLM_MODEL_NAME = "gpt-4-1106-preview"
    #OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"
    OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(self):
        # openAI 쪽 정의
        self.llmModel = ChatOpenAI(temperature=0.1, openai_api_key=config.OPENAI_API_KEY)
        self.embeddings = OpenAIEmbeddings(model=self.OPENAI_EMBEDDING_MODEL, openai_api_key=config.OPENAI_API_KEY)
        # text_splitter 정의 
        self.text_splitter = CharacterTextSplitter(chunk_size=512, chunk_overlap=50, separator= "\n\n\n")
        # Elastic Search 정리
        self.ES_INDEX_NAME = "research-test"
        self.ES_URL = config.ELASTIC_URL
        self.ES_USERNAME = config.ELASTIC_USER
        self.ES_PASSWORD = config.ELASTIC_PW
        self.es_client = Elasticsearch(hosts=[self.ES_URL], basic_auth=(self.ES_USERNAME, self.ES_PASSWORD))
        self.vectordb = ""

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant. Answer questions using only the following context. If you don't know the answer just say you don't know, don't make it up:\n\n{context}",
                ),
                ("human", "{question}"),
            ]
        )
        # chroma DB 기본 디렉토리 정의 
        self.persist_directory = './chroma_database/'
    # Unique ID 생성하기
    def generate_uuid_with_prefix(self):
        unique_id = "id_" + str(uuid.uuid4())
        return unique_id

    def call_multivector(self, query):
        prompt_text = """You are an assistant tasked with summarizing text. \
        Give a concise summary of the text. 대답은 한국어로 해줘. Text chunk: {element}""" 
        #result.metadata["title"] + result.metadata['header'] + result.metadata['table']
        #print(prompt_text)
        prompt = ChatPromptTemplate.from_template(prompt_text)
        # Summary chain
        model = self.llmModel
        chain = LLMChain(
            llm=model,
            prompt=prompt
        )
        answer = chain.run(query)
        return answer     
    

    async def ingest(self, file_path: str = None, file_type: str = None, file_name_itself: str = None, chunks: list = None):
        if file_path and file_type:
            if file_type == 'pdf':
                loader = PyPDFLoader(file_path=file_path)
                docs = loader.load()
                print("***********************")
                print(docs)
                if isinstance(docs, list):
                    text_list = [doc.page_content for doc in docs]
                    docs = "\n".join(text_list)
            elif file_type == 'docx':
                loader = Docx2txtLoader(file_path=file_path)
                docs = loader.load()
                docs = "\n".join(docs) if isinstance(docs, list) else docs
            else:
                raise ValueError("File path and file type must be provided.")

        doc =  Doc(page_content=docs, metadata={"source": file_name_itself})

        #chunk & 복잡한 거 일단 정규화 및 제거
        chunks = self.text_splitter.split_documents([doc])
        chunks = filter_complex_metadata(chunks) 
        print(chunks)

        #Data 넣어줄 것 잘 가공하기 
        vectors=[]
        id_vectors=[]
        meta = {}

        for doc in chunks:
            family_id = self.generate_uuid_with_prefix()
            text_id = self.generate_uuid_with_prefix()
            text_summary_id = self.generate_uuid_with_prefix() #요약만 따로 임베딩
        
            datas = {"id": text_summary_id, "vector": [], "text": "", "metadata": {}}
            meta = {}
            get_summary = self.call_multivector(doc.page_content)
            print("****** summary ******************************************************")
            print(get_summary)
            embeds = self.embeddings.embed_query(get_summary)
            print("****** embeds *************************************** ******************************************************")
            print(embeds)
            datas["text"] = get_summary
            datas["vector"] = embeds
            meta["text"] = get_summary
            meta["original_text"] = doc.page_content
            meta["text_title_yn"] = "Y"
            meta["table_yn"] = "N"
            meta["family_id"] = family_id
            meta["source"] = file_name_itself
            datas["metadata"] = meta              
            #요약 먼저  업데이트 
            self.es_client.update(body={"doc" : datas, "doc_as_upsert" : True}, index=self.ES_INDEX_NAME, id=datas["id"], upsert={"id": datas["id"]})
            
            print("************************[Summary Updated][Original Starts*********************************")
            
            datas = {"id": text_id, "vector": [], "text": "", "metadata": {}}
            meta = {}
            embeds = self.embeddings.embed_query(doc.page_content)  

            datas["vector"] = embeds
            datas["text"] = doc.page_content
            doc.metadata["text"] = doc.page_content
            meta["table_yn"] = "N"
            meta["text_title_yn"] = "N"
            meta["family_id"] = family_id
            meta["source"] = file_name_itself
            datas["metadata"] = meta        
            
            self.es_client.update(body={"doc" : datas, "doc_as_upsert" : True}, index=self.ES_INDEX_NAME, id=datas["id"], upsert={"id": datas["id"]})
        
########################################################################################
   
        self.es_client.indices.refresh(index="research-test")

        '''self.retriever = ElasticsearchStore(index_name=self.ES_INDEX_NAME, es_url=self.ES_URL, es_user=self.ES_USERNAME, es_password=self.ES_PASSWORD).as_retriever()(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.5},
        )'''


        
    async def ask(self, query: str):

        '''self.retriever = ElasticsearchStore(embedding=self.embeddings, index_name=self.ES_INDEX_NAME, es_url=self.ES_URL, es_user=self.ES_USERNAME, es_password=self.ES_PASSWORD).as_retriever()
        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | self.prompt
                      | self.llmModel
                      | StrOutputParser())
        result = self.retriever.get_relevant_documents(query)
        return result[0].page_content'''
        #vector = ElasticsearchStore.from_documents(embedding=self.embeddings, index_name=self.ES_INDEX_NAME, es_url=self.ES_URL, es_user=self.ES_USERNAME, es_password=self.ES_PASSWORD)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Answer the user's questions based on the below context:\n\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ])
        #document_chain = create_stuff_documents_chain(self.llmModel, prompt)
        #retrieval_chain = create_retrieval_chain(retriever_chain, document_chain)
        document_content_description = "market data research document"
        retriever = SelfQueryRetriever.from_llm(llm= self.llmModel, vectorstore=self.es_client, document_contents=document_content_description, verbose=True)
        #retriever_chain  = create_history_aware_retriever(self.llmModel, retriever, prompt)
        relevant_answer = retriever.get_relevant_documents(query)
        #response = retriever.invoke({"input": query})
        pprint(relevant_answer)
        return relevant_answer[0].page_content
        print(response[0].page_content)

   #########################################[(3RD GNB)(2ND LNB) AI 투자비서 화면 개발용 ]############################################    
    # 클라에서 파일 데이터 넘어온것 저장시키기
    async def ai_sec_file_control(self, file_path: str = None, file_type: str = None, file_name_itself: str = None, employeeId: str = None, chunks: list = None):
        # 파일 읽어서 
        if file_path and file_type:
            if file_type == 'pdf':
                loader = PyPDFLoader(file_path=file_path)
                docs = loader.load()
                print("***********************")
                print(docs)
                if isinstance(docs, list):
                    text_list = [doc.page_content for doc in docs]
                    docs = "\n".join(text_list)
            elif file_type == 'docx':
                loader = Docx2txtLoader(file_path=file_path)
                docs = loader.load()
                docs = "\n".join(docs) if isinstance(docs, list) else docs
            else:
                raise ValueError("File path and file type must be provided.")

        doc =  Doc(page_content=docs, metadata={"source": file_name_itself})

        ######## chunk & 복잡한 거 일단 정규화 및 제거 & 메타필드 추가
        chunks = self.text_splitter.split_documents([doc])
        chunks = filter_complex_metadata(chunks) 
        print(chunks)
            
        ######## 여기까지 파일데이터 읽기 끝                 
        ######## chroma DB에 넣기 시작
        user_persist_directory = os.path.join(self.persist_directory, employeeId)
        os.makedirs(user_persist_directory, exist_ok=True)
        
        # ChromaDB 클라이언트 초기화
        client = chromadb.PersistentClient(path=user_persist_directory)   
        
        # 파일이름 잘 넣어주기
        romanized_name = Romanizer(file_name_itself).romanize()
        formatted_name = romanized_name.replace(" ", "")
        formatted_name = ''.join(c if c.isalpha() else '_' for c in formatted_name)
        formatted_name = file_type.upper() + "_" + formatted_name
        print(formatted_name)
                
        # meta 값 만들어주기    
        try:
            collection = client.get_collection(employeeId)
            collection_metadata = collection.metadata
        except Exception as e:
            collection_metadata = {}    
        new_id_key = "id_1"  # 기본값
        for i in range(1, 9):  
            key = f"id_{i}"
            if key not in collection_metadata:
                new_id_key = key
                break
            elif i == 9:  
                new_id_key = key   
        new_metadata = {"hnsw:space": "cosine", new_id_key: formatted_name}                              
        self.vectordb = Chroma.from_documents(documents=chunks, embedding=self.embeddings, persist_directory=user_persist_directory, collection_name=employeeId, collection_metadata=new_metadata)

    # 클라에서 사번 던졌을때, 사번으로 만들어진 DB 검색해서 리턴해주기
    async def ai_sec_viewmydb(self, employeeId):
        user_persist_directory = os.path.join(self.persist_directory, employeeId)
        try:
            client = chromadb.PersistentClient(path=user_persist_directory)
            collection = client.get_collection(employeeId)
            collection_metadata = collection.metadata
            # 모든 id_x 값을 찾아서 리스트에 저장
            ids_found = []
            for i in range(1, 9):  # id_1부터 id_8까지만 탐색
                key = f"id_{i}"
                if key in collection_metadata:
                    ids_found.append(f"{key}: {collection_metadata[key]}")

            if ids_found:
                return {"message": "Success", "ids": ids_found}
            else:
                return {"message": "No ID keys found in collection metadata."}
        except Exception as e:
            raise e 

    # 클라에서 사번 던졌을때, 사번으로 만들어진 DB 클리어시키기
    '''async def ai_sec_clearmydb(self, employeeId):
        try:
            print("********************************************")
            user_persist_directory = os.path.join(self.persist_directory, employeeId)
            client = chromadb.PersistentClient(path=user_persist_directory)
            collections = client.list_collections()
            for collection in collections:
                client.delete_collection(name=collection.name)
            return "success"
        except Exception as e:
            return f"Failed to clear database: {e}"'''  

    async def ai_sec_clearmydb(self, employeeId):
        try:
            print("********************************************")
            user_persist_directory = os.path.join(self.persist_directory, employeeId)
            client = chromadb.PersistentClient(path=user_persist_directory)
            collections = client.list_collections()
            for collection in collections:
                client.delete_collection(name=collection.name)
            return "success"
        except Exception as e:
            return f"Failed to clear database: {e}"    
        
         
    # 클라에서 질문 왔을때 DB에서 similarity score 조회해서 답변해주기
    async def ai_sec_talk(self, query, employeeId):
        user_persist_directory = os.path.join(self.persist_directory, employeeId)
        client = chromadb.PersistentClient(path=user_persist_directory)
        collections = client.list_collections()   
        print(collections)     
        vectordb = Chroma(persist_directory=user_persist_directory, embedding_function=self.embeddings, collection_metadata={"hnsw:space": "cosine"})
       
        self.retriever = vectordb.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 3,
                "score_threshold": 0.1,
            },
        )
        print("cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc")       
        print(self.retriever.get_relevant_documents('query'))
        print(user_persist_directory)
        print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")       
        
        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | self.prompt
                      | self.llmModel
                      | StrOutputParser())
        
    # Assuming 'invoke' returns a result with a 'score' or similar metric
        result = self.chain.invoke(query)
        if not result :
            return "I'm sorry, I don't have enough information to answer that question accurately."
        else:
            return result          

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
        self.pinecone_index_name = None


        
chat_pdf_instance = ChatPDF()
hello = chat_pdf_instance.ai_sec_viewmydb("3321130")
print(hello)

    # 함수 실행
#chat_pdf_instance.test_retrieve_document() 
#print(chat_pdf_instance.ask("who is the author of this document?"))
