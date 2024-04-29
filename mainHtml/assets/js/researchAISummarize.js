//******************************** 3RD GNB::  AI 투자비서 Starts **********************************************//      
//사번 넣고 확인버튼
function confirmEmployeeId() {
    var employeeIdInput = document.getElementById('ai_invest_sec_employeeId');
    var employeeId = employeeIdInput.value;
    if (employeeId.length !== 7) {
        alert("사번을 제대로 입력해주세요");
    } else {
        document.getElementById('ai_invest_sec_mainContent').style.opacity = "1";
        aiSecViewMyDB();
    }
}
// 사번으로 생성된 벡터 DB 컬렉션 조회해오기 
async function aiSecViewMyDB() {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    try {
        const response = await fetch('/rag/ai-sec-viewmydb/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({employeeId: employeeId}),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        console.log(result);
        const container = document.getElementById('ai_invest_sec_appliedData');
        container.innerHTML = ""; 
        if (result.result && result.result.collections) {
            result.result.collections.forEach((collectionObj, index) => {
                const collectionName = collectionObj.collection_name;
                const splitName = collectionName.split('_');
                const type = splitName[1]; // 예: 'PDF'
                const value = splitName.slice(2).join('_'); // 예: '1', 'BQE_EquityBase'
                appendData(index + 1, type, value);
            });
        } else {
            container.innerHTML = `<p class="ai_no_data">현재 적용된 데이터가 없습니다.</p>`;
        }
    } catch (error) {
        console.error("Fetch error: " + error.message);
        document.getElementById('ai_invest_sec_appliedData').innerHTML = `<p class="ai_error_message">데이터를 불러오는 중 오류가 발생했습니다: ${error.message}</p>`;
    }            
}
// DB 클리어 시키기 함수
async function clearDB(){
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    try {
        const response = await fetch('/rag/ai-sec-cleardb/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({employeeId: employeeId}),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        if (result.result === "success") {
            document.getElementById('ai_invest_sec_appliedData').innerHTML = `<div class="header-with-button"><p>◎ MY DB 적용 데이터</p><button onclick="clearDB()" class="db-clear-btn">DB 클리어</button></div>`;
        } else {
            console.error("No message received from the ai sec rag server.");
        }
    } catch (error) {
        console.error("Fetch error: " + error.message);
    }   
}


// '적용' 버튼 클릭 시 웹사이트 및 YouTube URL 적용
function applyWeb() {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    var url = document.getElementById('ai_invest_sec_websiteUrl').value;
    appendData("웹사이트 주소", url);
}
function readYoutubeScript(actionType = 'read') {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    var url = document.getElementById('ai_invest_sec_youtubeUrl').value;
    const contentArea = document.getElementById('aiSecLayerPopupContent');  

    var loadingText = document.getElementById('loading_research_ai_text');
    loadingText.textContent = 'Youtube 스크립트 수집중입니다.';
    document.getElementById('loading_bar_research_ai').style.display = 'block';

    fetch('/api/youtube_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ video_id_or_url: url, type: actionType })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('loading_bar_research_ai').style.display = 'none';
        let transcript = data.transcript || 'Error loading data';
        // Replace occurrences of '니다' or '세요' with themselves followed by a line break
        transcript = transcript.replace(/(니 다|세 요)/g, '$1\n');
        contentArea.innerText = transcript;
        toggleLayerPopup();
    })
    
    .catch(error => {
        console.error('Error:', error);
        alert("Youtube 네트워킹에 실패했습니다.")
        document.getElementById('loading_bar_research_ai').style.display = 'none';
    });      
    appendData("YouTube URL", url);
}

function applyYT() {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    appendData("YouTube URL", url);
}

function toggleLayerPopup() {
    //const popup = document.getElementById('aiSecLayerPopup');
    //popup.style.display = popup.style.display === 'block' ? 'none' : 'block';
    $('#aiSecLayerPopup').dialog({
        dialogClass : 'research-dialog',
        title : '',
        modal : true,
        draggable : false,
        resizable : false,
        autoOpen: false,
        width: 700,
        height: 700,
        open : function(){
            $('.ui-widget-overlay').on('click', function(){
                $('#dialog-sample').dialog('close');
            });
        }
    });

    $('#aiSecLayerPopup').dialog('open');

}
function appendData(index, type, value) {
    var container = document.getElementById('ai_invest_sec_appliedData');
    const displayValue = value !== "1" ? `${type} - ${value}` : type;
    if(container.innerHTML === "") {
        container.innerHTML += `<div class="header-with-button"><p>◎ MY DB 적용 데이터</p><button onclick="clearDB()" class="db-clear-btn">DB 클리어</button></div>`;
    }                
    container.innerHTML += `<p class="ai_append_text">[나의 DB에 적용된 데이터 #${index}] ${displayValue}</p>`;
}           
function triggerAiFileInput() {
    document.getElementById('aiSecFileInput').click();
}
function handleAiFileUpload(files) {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }                
    const file = files[0]; 
    //appendData("나의 DB에 적용된 데이터", files[0].name);
    uploadAiFileToServer(file);
}            
// 파일 서버로 업로드시키기
function uploadAiFileToServer(file) {
    let formData = new FormData();
    formData.append("file", file); 
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    formData.append("employeeId", employeeId);
    fetch('/rag/ai-sec-upload/', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        aiSecViewMyDB();
    })
    .catch((error) => {
        console.error('Error:', error);
    });
} 
//채팅 질의 답변 함수 
async function aiSecTalk() {
    const messageInput = document.getElementById('aiSecInput');
    const message = messageInput.value;
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    messageInput.value = '';
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    aiSecChatDisplay(message, 'sent');
    const loadingDiv = displayTypingIndicator(); // 타이핑 인디케이터를 화면에 표시하고, 해당 div를 반환받음
    try {
        const response = await fetch('/rag/ai-sec-talk/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: message, employeeId: employeeId}),
        });
        clearTypingIndicator(loadingDiv); // 응답이 오면 타이핑 인디케이터를 삭제
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        if (result.message) {
            aiSecChatDisplay(result.result, 'received'); 
        } else {
            console.error("No message received from the ai sec rag server.");
        }
    } catch (error) {
        console.error("Fetch error: " + error.message);
    }            
}
// 챗 답변 보여주는 함수
function aiSecChatDisplay(messageText, sender) {
    const messagesContainer = document.querySelector('.ai-sec-messages');            
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('ai-sec-message', `ai-sec-${sender}`);
    
    const messageTextDiv = document.createElement('div');
    messageTextDiv.classList.add('ai-sec-text');
    messageTextDiv.textContent = messageText;
    
    messageWrapper.appendChild(messageTextDiv);
    messagesContainer.appendChild(messageWrapper);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 답변 생성중입니다 메시지 처리 함수 
function displayTypingIndicator() {
    const messagesContainer = document.querySelector('.ai-sec-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.classList.add('ai-sec-message', 'ai-sec-received', 'loading');
    loadingDiv.style.backgroundColor = '#FFF3CD'; // 연주황색 배경 설정
    messagesContainer.appendChild(loadingDiv);
    
    const loadingSpan = document.createElement('span');
    const loadingText = '열심히 답변 생성중입니다 ';
    let loadingTextIndex = 0;
    
    loadingDiv.interval = setInterval(() => {
        loadingSpan.textContent = loadingText.substring(0, loadingTextIndex) + '_';
        loadingTextIndex++;
        if (loadingTextIndex > loadingText.length) loadingTextIndex = 0;
    }, 150);
    
    loadingDiv.appendChild(loadingSpan);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return loadingDiv;
}

function clearTypingIndicator(loadingDiv) {
    clearInterval(loadingDiv.interval); 
    loadingDiv.remove(); 
}  
//******************************** 3RD GNB::  AI 투자비서 Ends **********************************************//          