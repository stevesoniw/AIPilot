from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from langchain.vectorstores.utils import filter_complex_metadata
import config
import os
import chromadb

#https://research-test-ki113xk.svc.gcp-starter.pinecone.io
class ChatPDF:
    vector_store = None
    retriever = None
    chain = None
    '''pinecone_api_key = config.PINE_CONE_AGENT_API
    pinecone_index_name = "research-test"
    pinecone_environment = "gcp-starter"'''

    CUR_DIR = os.path.dirname(os.path.abspath(__file__))
    CHROMA_PERSIST_DIR = os.path.join(CUR_DIR, 'chroma_persist')
    CHROMA_COLLECTION_NAME= "research-test"
    '''chroma_client = chromadb.HttpClient(host="localhost", port=8001)
    collection = chroma_client.create_collection(name="my_test_collection")
    print(chroma_client.list_collections())'''

    def __init__(self):
        # openAI 쪽 정의
        self.model = ChatOpenAI(temperature=0.1, openai_api_key=config.OPENAI_API_KEY)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=config.OPENAI_API_KEY)
        # text_splitter 정의 
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=100)
        ''' pinecone 정리
        self.pc = Pinecone(api_key=self.pinecone_api_key, environment=self.pinecone_environment)
        self.index_name = self.pinecone_index_name
        self.index = self.pc.Index(self.index_name)'''
        client = chromadb.PersistentClient()
        post = client.create_collection(
            name="research-test"
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant. Answer questions using only the following context. If you don't know the answer just say you don't know, don't make it up:\n\n{context}",
                ),
                ("human", "{question}"),
            ]
        )

    def ingest(self, pdf_file_path: str):
        docs = PyPDFLoader(file_path=pdf_file_path).load()
        chunks = self.text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)
        #embed = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=config.OPENAI_API_KEY)
        vector_store = Chroma.from_documents(documents=chunks, embedding=OpenAIEmbeddings(openai_api_key=config.OPENAI_API_KEY), persist_directory=self.CHROMA_PERSIST_DIR,
        collection_name=self.CHROMA_COLLECTION_NAME)

        #vector_store = PineconeVectorStore.from_documents(chunks, self.embeddings, index_name=self.index )
        self.retriever = vector_store.as_retriever(
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

    def ask(self, query: str):
        if not self.chain:
            return "Please, add a PDF document first."

        return self.chain.invoke(query)

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
        self.pinecone_index_name = None

