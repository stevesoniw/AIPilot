import streamlit as st
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import UnstructuredFileLoader
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain.docstore.document import Document as Doc
import multiprocessing
import asyncio


### 계속 써먹을 코드라서 함수처리
def create_summary(docs):
    # Define prompt
    prompt_template = """You are an assistant tasked with summarizing analyst reports.
    애널리스트 리포트를 줄 건데, 이 리포트를 보고 다음을 분석해줘.

    1. 어느 증권사에서 발행했고, 언제 발행했고, 몇분기 (ex. 20xx년 x분기) 에 대해서 어떤 기업에 대해 분석한 건지 첫 문장에서 알려줘.
    2. 이 리포트의 주요 사항들을 사업별로 Bullet Point 형식으로 3가지 이상 알려줘. 주요사항들을 왜 그렇게 판단했는지 그 근거도 찾아서 보여줘.
    3. 이 회사의 Bull, Bear 포인트들을 회사의 사업 분야별로 표로 정리해서 보여줘. 사업 분야라는 건 회사의 주요 사업들을 얘기하는 거야.

    대답은 한국어로 해줘.

    답변은 800자 이내로 해줘.

    리포트에 없는 내용은 언급하지 마.

    리포트 내용:
    "{text}"

    답변: """
    prompt = PromptTemplate.from_template(prompt_template)

    # Define LLM chain
    llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo-preview")
    llm_chain = LLMChain(llm=llm, prompt=prompt)

    # Define StuffDocumentsChain
    stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="text")
    # loader = PyPDFLoader(doc_path)
    # docs = loader.load()
    result = stuff_chain.run(docs)
    
    print(result)
    return result

with st.sidebar:
    uploaded_files = st.file_uploader("리서치리포트 업로드", accept_multiple_files=True, type=None)
    
    st.markdown(
    """ 주의사항
    - PDF 업로드할 때 여러 파일을 올리고싶으신 경우 한번에 여러 개를 선택해 업로드해주세요.
    - 이미 업로드한 파일 외 더 추가하고 싶은 파일이 있으시면 새로고침을 하고 업로드해주세요.
    - 프롬프트 예시에서 프롬프트를 선택한 후 커스텀 프롬프트를 입력하고 싶을 경우 반드시 예시를 삭제한 후에 프롬프트를 입력해주세요.
    
    """     
    )

    
# Chat UI title
st.header("리서치 리포트 분석")
st.subheader("PDF 포맷의 리서치 리포트를 여러 개 업로드해 분석할 수 있는 도구입니다.")



# File uploader in the sidebar on the left

llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo-preview",streaming=True)

        

# Check if files are uploaded
if uploaded_files:
    # Print the number of files to console
    print(f"Number of files uploaded: {len(uploaded_files)}")

    # Load the data and perform preprocessing only if it hasn't been loaded before
    if "processed_data" not in st.session_state:
        # Load the data from uploaded PDF files
        documents = []
        for uploaded_file in uploaded_files:
            # Get the full file path of the uploaded file
            file_path = os.path.join(os.getcwd(), uploaded_file.name)

            # Save the uploaded file to disk
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            # Use UnstructuredFileLoader to load the PDF file
            loader = PyPDFLoader(file_path)
            # loader = UnstructuredFileLoader(file_path)
            loaded_documents = loader.load()
            print(f"Number of pages loaded: {len(loaded_documents)}")
            print("******************************************")
            print(loaded_documents)
            print("******************************************")
            # Extend the main documents list with the loaded documents
            documents.extend([loaded_documents])
            print(documents)

        # Store the processed data in session state for reuse
        st.session_state.processed_data = {
            "document": documents
            # "vectorstore": vectorstore,
        }

        # # Print the number of total chunks to console
        # print(f"Number of total chunks: {len(document_chunks)}")

    else:
        # If the processed data is already available, retrieve it from session state [[Document(ssss), Document]]
        document_chunks = st.session_state.processed_data["document"]
        # vectorstore = st.session_state.processed_data["vectorstore"]

    ## 프롬프트 예시 제공 (단일파일, 멀티파일에 따라 프롬프트가 다름)
    if len(uploaded_files) == 1:
        option = st.selectbox(
        "프롬프트 예시",
        ("리포트를 읽고 해당 기업의 Bull, Bear 포인트를 사업분야 별로 표로 정리해줘.",
        "리포트를 읽고 해당 기업의 이번 분기 실적이 어땠는지 알려줘. 뭘 근거로 리포트에서 그렇게 판단했는지도 알려줘.",
        "리포트에 쓰인 전문 용어가 있으면 설명해줘. PER, EPS, PBR 같은 주식 용어나 투자지표는 이미 알고 있으니까 생략해줘. 이 기업에서 하는 사업과 관련된 용어들 중에 생소한 것들은 꼭 알려줘. 예를 들어 LG화학이면 제품 개발하는 데 쓰인 과학 기술이나 과학 용어 같은 걸 알려줘."),
        index=None,
        placeholder="드롭다운 바에서 예시 프롬프트를 선택하거나 채팅바에 커스텀 프롬프트를 입력하세요.",
        )
    else:
        option = st.selectbox(
        "프롬프트 예시",
        ("리포트들을 보고 해당 기업의 Bull, Bear 포인트들을 사업부 별로 정리해서 표로 보여줘.",
        """각 리포트에서 공통적으로 언급되는 주제/키워드를 몇가지 선정하고, 의견이 일치하는 부분과 일치하지 않는 부분을 정리해줘. 
        하위 문장의 구분은 숫자가 아닌 '•'으로 구분해주고 개별 문장은 한문장씩 끊어서 답변하되 '-합니다', '-입니다'는 빼고 문장을 만들어줘.""",
        """각 리포트들에서 전문용어/약어를 사용한 경우 이에 대한 설명을 추가해줘.
        앞으로 용어를 설명할 때 '-입니다', '-됩니다'는 빼고 간결하게 대답해줘.
        답변의 시작은 "<용어 설명>"으로 하고, 용어들은 1,2,3 순서를 매겨서 알려줘.
        정리할 때, 재무적 용어 (ex. QoQ, YoY)나 리포트용 약어는 제외하고 정리해줘."""),
        index=None,
        placeholder="드롭다운 바에서 예시 프롬프트를 선택하거나 채팅바에 커스텀 프롬프트를 입력하세요.",
        )
    print(option)   
     
    # st.write('You selected:', option)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    
    
    if prompt := st.chat_input("프롬프트 예시를 선택하셨다면 예시를 삭제한 후 커스텀 프롬프트를 작성해주세요.") or option != None:
        print("Option is: " + str(option))
        if option != None:
            prompt = option
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Query the assistant using the latest chat history
        
        print("prompt is: "+ prompt)
        if len(uploaded_files) == 1: #단일리포트
            print("***********단일 리포트**************")
            # if option:
            #     prompt = option
            #     option = False
            prompt_template = """너는 애널리스트 리포트에 대해 분석하는 리포트 전문가야.
            애널리스트 리포트를 줄 건데, 이 리포트를 보고 다음 요구사항에 맞춰서 리포트를 분석해줘. \n""" + """요구사항: """ + prompt+ """
            
            대답은 한국어로 해줘.

            답변은 800자 이내로 해줘.

            리포트에 없는 내용은 언급하지 마.

            리포트 내용:
            "{text}"

            답변: """
            modified_prompt = PromptTemplate.from_template(prompt_template)
            print(modified_prompt)
            llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo-preview")
            llm_chain = LLMChain(llm=llm, prompt=modified_prompt, verbose=True) ### prompt = 유저가 입력한거
            # print(document_chunks)
            stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="text")
            result = stuff_chain.run(document_chunks[0])
            
        else: ## 멀티리포트
            print("*****멀티리포트******")
            with st.spinner('각 리포트를 하나씩 확인해볼게요...'):
                print(document_chunks)
                with multiprocessing.Pool(processes=len(document_chunks)) as pool: #병렬처리 고고
                    results = [pool.apply_async(create_summary, (document,)) for document in document_chunks]
                    final_results = [Doc(page_content=result.get()) for result in results]
                    print("Final Results:", final_results)
    
            with st.spinner('리포트들을 다 확인했으니 답변을 조합해볼게요...'):
                prompt_template = """너는 애널리스트 리포트에 대해 분석하는 리포트 전문가야.
                애널리스트 리포트를 줄 건데, 이 리포트를 보고 다음 요구사항에 맞춰서 리포트를 분석해줘. \n""" + """요구사항: """ + prompt+ """
                
                대답은 한국어로 해줘.

                답변은 800자 이내로 해줘.

                리포트에 없는 내용은 언급하지 마.

                리포트 내용:
                "{text}"

                답변: """
                modified_prompt = PromptTemplate.from_template(prompt_template)
                print(modified_prompt)
                llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo-preview", streaming=True)
                llm_chain = LLMChain(llm=llm, prompt=modified_prompt, verbose=True) ### prompt = 유저가 입력한거
                # print(document_chunks)
                stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="text")
                result = stuff_chain.run(final_results)
                
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            full_response = result
        message_placeholder.markdown(full_response)    
        print(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})


else:
    st.write("왼쪽 상단에서 리서치 리포트를 업로드해주세요.")