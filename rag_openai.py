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
from elasticsearch import Elasticsearch
# 기본 유틸
import config
import os
import uuid

#https://research-test-ki113xk.svc.gcp-starter.pinecone.io


class ChatPDF:
    vector_store = None
    retriever = None
    chain = None
    LLM_MODEL_NAME = "gpt-4-1106-preview"
    OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"

    def __init__(self):
        # openAI 쪽 정의
        self.model = ChatOpenAI(temperature=0.1, openai_api_key=config.OPENAI_API_KEY)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=config.OPENAI_API_KEY)
        # text_splitter 정의 
        self.text_splitter = CharacterTextSplitter(chunk_size=1024, chunk_overlap=100, separator= "\n\n\n")
        # Elastic Search 정리
        self.ES_INDEX_NAME = "research-test"
        self.ES_URL = config.ELASTIC_URL
        self.ES_USERNAME = config.ELASTIC_USER
        self.ES_PASSWORD = config.ELASTIC_PW
        self.es_client = Elasticsearch(hosts=[self.ES_URL], basic_auth=(self.ES_USERNAME, self.ES_PASSWORD))

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant. Answer questions using only the following context. If you don't know the answer just say you don't know, don't make it up:\n\n{context}",
                ),
                ("human", "{question}"),
            ]
        )
    # Unique ID 생성하기
    def generate_uuid_with_prefix():
        unique_id = "id_" + str(uuid.uuid4())
        return unique_id

    def call_multivector(self, query):
        prompt_text = """You are an assistant tasked with summarizing text. \
        Give a concise summary of the text. 대답은 한국어로 해줘. Text chunk: {element}""" 
        #result.metadata["title"] + result.metadata['header'] + result.metadata['table']
        #print(prompt_text)
        prompt = ChatPromptTemplate.from_template(prompt_text)
        # Summary chain
        model = ChatOpenAI(temperature=0, model=self.LLM_MODEL_NAME)
        chain = LLMChain(
            llm=model,
            prompt=prompt
        )
        answer = chain.run(query)
        return answer     
    
    # chunk neat하게 
    def processChunks(self,chunks):
        for doc in chunks:
            family_id = self.generate_uuid_with_prefix()
            text_id = self.generate_uuid_with_prefix()
            text_summary_id = self.generate_uuid_with_prefix() #요약만 따로 임베딩
        
            datas = {"id": text_summary_id, "vector": [], "text": "", "metadata": {}}
            meta = {}
            get_summary = self.call_multivector(doc.page_content)

            embeds = self.embeddings.embed_query(get_summary)["result"]["embedding"]   
            
            query_result = self.es_client.search(index=self.ES_INDEX_NAME, body=embeds)
            
            datas["text"] = get_summary
            datas["vector"] = embeds

            meta["text"] = get_summary
            meta["original_text"] = doc.page_content
            meta["text_title_yn"] = "Y"
            meta["table_yn"] = "N"
            meta["family_id"] = family_id
            meta["source"] = file_name
            datas["metadata"] = meta      

  

    async def ingest(self, file_path: str = None, file_type: str = None, file_name_itself: str = None, chunks: list = None):
        if file_path and file_type:
            if file_type == 'pdf':
                docs = PyPDFLoader(file_path=file_path)
            elif file_type == 'docx':
                loader = Docx2txtLoader(file_path=file_path)
                docs = loader.load()
            else:
                raise ValueError("File path and file type must be provided.")

        doc =  Doc(page_content=docs, metadata={"source": file_name_itself})

        #chunk & 복잡한 거 일단 정규화 및 제거
        chunks = self.text_splitter.split_documents(doc)
        chunks = filter_complex_metadata(chunks) 
        print(chunks)

        returnData = self.processChunks(chunks, file_name_itself)

        vectors=[]
        id_vectors=[]
        meta = {}
            

            
        if chunks is None:
            raise ValueError("Either a pdf_file_path must be provided or chunks of text.")


########################################################################################
        

        vector_store = ElasticsearchStore(
            es_url=self.ES_URL,
            es_user=self.ES_USERNAME,
            es_password=self.ES_PASSWORD,
            embedding=self.embeddings,
            index_name="research-test",
        )

        #document_ids = vector_store.add_documents(documents=chunks)  
        document_ids = vector_store.add_embeddings(body={"doc" : chunks, "doc_as_upsert" : True})  
        
        print(f"Indexed documents with IDs: {document_ids}")

        # Refresh index to make sure all documents are searchable
        self.es_client.indices.refresh(index="research-test")

        self.retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.5},
        )

        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | self.prompt
                      | self.model
                      | StrOutputParser())

    def ask(self, query: str):
        if not self.chain:
            return "Please, add a PDF document first."
        print(self.chain.invoke(query))
        return self.chain.invoke(query)

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
        self.pinecone_index_name = None


        
chat_pdf_instance = ChatPDF()
#chat_pdf_instance.test()
    # 함수 실행
#chat_pdf_instance.test_retrieve_document() 
print(chat_pdf_instance.ask("who is the author of this document?"))
