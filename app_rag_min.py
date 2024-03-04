from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_pinecone import PineconeVectorStore

from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from langchain.vectorstores.utils import filter_complex_metadata

import os, time
from pinecone import Pinecone, PodSpec
from dotenv import load_dotenv

class ChatPDF:
    vector_store = None
    retriever = None
    chain = None

    def __init__(self):
        load_dotenv() #ENV Load
        
        self.pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        self.vector_store = None
        self.model = ChatOpenAI(temperature=0.1)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=100)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant. Answer questions using only the following context. If you don't know the answer just say you don't know, don't make it up:\n\n{context}",
                ),
                ("human", "{question}"),
            ]
        )
        
    def index_list(self):
        return self.pc.list_indexes().names()
    
    def ingest(self, pdf_file_path: str, pc_index_name: str):
        if not pc_index_name :
            raise Exception("Please, input Pinecone index name!")
       
        docs = PyPDFLoader(file_path=pdf_file_path).load()
        chunks = self.text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)
        
        # check if index already exists (it shouldn't if this is first time)
        if pc_index_name not in self.index_list():
            # if does not exist, create index
            self.pc.create_index(
                pc_index_name,
                dimension=1536,
                metric="cosine",
                spec=PodSpec(
                    environment="gcp-starter",
                    pod_type="starter",
                    pods=1
                )
            )
            # wait for index to be initialized
            while not self.pc.describe_index(pc_index_name).status['ready']:
                time.sleep(1)
         
        self.vector_store = PineconeVectorStore.from_documents(documents=chunks, embedding=OpenAIEmbeddings(), index_name=pc_index_name)
        
    def ask(self, query: str, pc_index_name: str):
        if not pc_index_name :
            return "Please, input Pinecone index name."
        
        if self.vector_store == None :
            try:
                self.vector_store = PineconeVectorStore.from_existing_index(embedding=OpenAIEmbeddings(), index_name=pc_index_name)
            except Exception as e:
                return f"Pincecone Excption : {e}"
            
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 3,
                "score_threshold": 0.5,
            },
        )
        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | self.prompt
                      | self.model
                      | StrOutputParser())

        if not self.chain:
            return "Please, add a PDF document first."

        return self.chain.invoke(query)

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
