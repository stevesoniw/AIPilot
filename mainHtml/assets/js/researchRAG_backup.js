//******************************** 3RD GNB::  리서치RAG Starts **********************************************//
//파일 업로드
async function uploadRagFile() {
    const formData = new FormData();
    const fileRagInput = document.getElementById('fileRagInput');
    formData.append("file", fileRagInput.files[0]);
    document.getElementById('loading_bar_rag').style.display = 'block';
    const response = await fetch('/upload-file/', {
        method: 'POST',
        body: formData,
    }).finally(() => {
        // 로딩 바 숨김
        document.getElementById('loading_bar_rag').style.display = 'none';
    });
    const result = await response.json();
    console.log(result);
}
//채팅 답변 요청 
async function ragSendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value;
    messageInput.value = '';
    ragChatDisplay(message, 'sent')
    try {
        const response = await fetch('/process-message/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: message}),
        });
        if (!response.ok) {
            throw new Error(`RAG HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        if (result.message) {
            console.log(result.message);
            // 답변온것 보여주는 영역
            const newMessage = document.createElement('div');
            newMessage.classList.add('rag-message', 'rag-received');
            const messageTextDiv = document.createElement('div');
            messageTextDiv.classList.add('rag-text');
            messageTextDiv.textContent = result.message;
            newMessage.appendChild(messageTextDiv);
            document.querySelector('.rag-messages').appendChild(newMessage);
        } else {
            console.error("No message received from the RAG server.");
            const defaultMsg = "No response from the RAG server.";
        }
    } catch (error) {
        console.error("RAG Fetch error: " + error.message);
    }            
    //document.getElementById('response').innerText = result.message;
}
// 채팅 화면에 뿌려주기
function ragChatDisplay(messageText, sender = 'sent') {
    const inputField = document.querySelector('.rag-chat-input input');
    const messagesContainer = document.querySelector('.rag-messages');            
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('rag-message', `rag-${sender}`);

    const messageTextDiv = document.createElement('div');
    messageTextDiv.classList.add('rag-text');
    messageTextDiv.textContent = messageText;

    messageWrapper.appendChild(messageTextDiv);
    messagesContainer.appendChild(messageWrapper);
    messagesContainer.scrollTop = messagesContainer.scrollHeight; 
}       
//******************************** 3RD GNB::  리서치RAG Ends   ***********************************************//   