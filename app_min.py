import os
import config
import tempfile
import streamlit as st
from streamlit_chat import message
from app_rag_min import ChatPDF

st.set_page_config(page_title="ChatPDF")

def display_messages():
    st.subheader("Chat")
    for i, (msg, is_user) in enumerate(st.session_state["messages"]):
        message(msg, is_user=is_user, key=str(i))
    st.session_state["thinking_spinner"] = st.empty()


def process_input():
    if st.session_state["user_input"] and len(st.session_state["user_input"].strip()) > 0:
        user_text = st.session_state["user_input"].strip()
        with st.session_state["thinking_spinner"], st.spinner(f"Thinking"):
            agent_text = st.session_state["assistant"].ask(user_text, select_pc_index_name())

        st.session_state["messages"].append((user_text, True))
        st.session_state["messages"].append((agent_text, False))

def read_and_save_file():
    st.session_state["assistant"].clear()
    st.session_state["messages"] = []
    st.session_state["user_input"] = ""

    for file in st.session_state["file_uploader"]:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(file.getbuffer())
            file_path = tf.name

        with st.session_state["ingestion_spinner"], st.spinner(f"Ingesting {file.name}"):
            try:
                st.session_state["assistant"].ingest(file_path, select_pc_index_name())
            except Exception as e :
                st.toast(f'Exception : {e}', icon='🚨')  
        os.remove(file_path)
           
            
def select_pc_index_name():
    if st.session_state["pc_index_name"] and len(st.session_state["pc_index_name"].strip()) > 0:
        return st.session_state["pc_index_name"].strip()
    return ""

def is_select_pc_index_create():
    return "Create index" == st.session_state["select_pc_index"]

def select_pc_index_change():
    if is_select_pc_index_create():
        st.session_state["pc_index_name"] = ""
    else:
        st.session_state["pc_index_name"] = st.session_state["select_pc_index"]
        
def page():
    if len(st.session_state) == 0:
        st.session_state["messages"] = []
        st.session_state["assistant"] = ChatPDF()

    st.header("ChatPDF")

    st.subheader("Upload a document")
    
    col1, col2 = st.columns(2)
    with col1:
        options = []
        options.extend(st.session_state["assistant"].index_list())
        options.append('Create index')
        select_index = st.selectbox(
            "Select Pinecone Index",
            options,
            key="select_pc_index",
            placeholder="Select Pinecone Index",
            on_change=select_pc_index_change
        )
        
        if select_index == 'Create index':
            select_index = ""

    with col2:
        st.text_input(
            "Pinecone Index Name",
            key="pc_index_name",
            placeholder='Input Pinecone Index Name..',
            value=select_index,
            disabled=not is_select_pc_index_create()
        )
    st.file_uploader(
        "Upload document",
        type=["pdf"],
        key="file_uploader",
        on_change=read_and_save_file,
        label_visibility="collapsed",
        accept_multiple_files=True,
    )
    st.session_state["ingestion_spinner"] = st.empty()
    
    display_messages()
    st.text_input("Message", key="user_input", on_change=process_input)

if __name__ == "__main__":
    page()
