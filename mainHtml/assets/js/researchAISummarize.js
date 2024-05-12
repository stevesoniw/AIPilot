//******************************** 3RD GNB::  AI 투자비서 Starts **********************************************//      
//사번 넣고 확인버튼
function confirmEmployeeId() {
    var employeeIdInput = document.getElementById('ai_invest_sec_employeeId');
    var employeeId = employeeIdInput.value;
    if (employeeId.length !== 7) {
        alert("사번을 제대로 입력해주세요");
    } else {
        document.getElementById('ai_invest_sec_mainContent').style.opacity = "1";
        document.getElementById('ai_invest_sec_applyWeb').style.opacity = "0.5";
        document.getElementById('ai_invest_sec_applyYT').style.opacity = "0.5";
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
                appendData(index + 1, type, value, employeeId);
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
        var loadingText = document.getElementById('loading_research_ai_text');
        loadingText.textContent = 'DB 데이터를 리셋하고 있습니다.';
        document.getElementById('loading_bar_research_ai').style.display = 'block';        
        const response = await fetch('/rag/ai-sec-cleardb/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({employeeId: employeeId}),
        });
        if (!response.ok) {
            document.getElementById('loading_bar_research_ai').style.display = 'none'; 
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        if (result.result === "success") {
            alert("DB 데이터가 Clear 되었습니다!");
            removeAllDivsByClass('ai-sec-text');
            document.getElementById('loading_bar_research_ai').style.display = 'none'; 
            document.getElementById('ai_invest_sec_appliedData').innerHTML = `<div class="header-with-button"><p>◎ MY DB 적용 데이터</p><button onclick="clearDB()" class="db-clear-btn">DB 클리어</button></div>`;
        } else {
            document.getElementById('loading_bar_research_ai').style.display = 'none'; 
            console.error("No message received from the ai sec rag server.");
        }
    } catch (error) {
        document.getElementById('loading_bar_research_ai').style.display = 'none'; 
        console.error("Fetch error: " + error.message);
    }   
}
// 채팅내역도 같이 지워주자ㅋㅋ
function removeAllDivsByClass(className) {
    const elements = document.querySelectorAll(`div.${className}`);
    if (elements.length > 0) {
        elements.forEach(element => {
            element.parentNode.removeChild(element);
        });
    } else {
        console.log(`No elements found with class: ${className}`);
    }
}


// '적용' 버튼 클릭 시 웹사이트 및 YouTube URL 적용
async function applyWebToDB(file_type) {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    let savedTranscript = "";
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    var webSiteUrl = document.getElementById('ai_invest_sec_websiteUrl').value;
    var youTubeUrl = document.getElementById('ai_invest_sec_youtubeUrl').value;
    var domain;    
    console.log(webSiteUrl);
    console.log(youTubeUrl);
    if(file_type=='website'){
        savedTranscript = document.getElementById('webSiteHidden').getAttribute('data-transcript');
        try {
            domain = new URL(webSiteUrl);
            console.log("domain====", domain);
            if (!webSiteUrl.trim() || !domain) {
                alert('올바른 형식의 URL이 아닙니다. 다시 입력해주세요!');
                return;
            }
            domain = domain.hostname; 
        } catch (error) {
            alert('올바른 형식의 URL이 아닙니다. 다시 입력해주세요!');
            return; 
        }        
    }else if(file_type== 'youtube'){
        savedTranscript = document.getElementById('youTubeHidden').getAttribute('data-transcript');
        try {
            const urlObj = new URL(youTubeUrl);
            let videoId = "youtubeData";
            console.log("urlObj====", urlObj);
            if (urlObj.hostname === "youtu.be") {
                videoId = urlObj.pathname.substring(1); // 경로에서 첫 번째 '/' 제거
            } else if (urlObj.hostname === "www.youtube.com" || urlObj.hostname === "youtube.com") {
                videoId = urlObj.searchParams.get("v"); // 쿼리 매개변수에서 'v' 값을 가져옴
            }
            domain = videoId;
        } catch (error) {
            alert('올바른 형식의 YouTube URL이 아닙니다. 다시 입력해주세요!');
            return;
        }        
    }
    var loadingText = document.getElementById('loading_research_ai_text');
    loadingText.textContent = '웹사이트 DATA 저장중입니다.';
    document.getElementById('loading_bar_research_ai').style.display = 'block';
    try{
        const response = await  fetch('/rag/website_db_register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ employeeId: employeeId, savedTranscript: savedTranscript, domain: domain, file_type : file_type }),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        console.log(result);
        if (result.message === "Success") {
            alert(`${file_type === 'website' ? 'Website' : 'YouTube'} Data가 저장되었습니다.`);
            document.getElementById('loading_bar_research_ai').style.display = 'none';        
        }else {
            console.error("Website Data Register Failed");
            alert("Website Data 저장에 실패했습니다.")
            document.getElementById('loading_bar_research_ai').style.display = 'none';        
        }
    } catch (error) {
        console.error("Fetch error: " + error.message);
        document.getElementById('loading_bar_research_ai').style.display = 'none';        
    }     
    //DB 데이터 다시조회
    aiSecViewMyDB();
}

function readWebSite(actionType, llm_model) {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    var url = document.getElementById('ai_invest_sec_websiteUrl').value;
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    if (url.length < 5 || !url.startsWith('http')) {
        alert("URL을 정확하게 입력해주세요! (*http부터 입력)");
        return;
    }        
    const contentArea = document.getElementById('aiSecLayerPopupContent');  
    contentArea.innerText = "";

    var loadingText = document.getElementById('loading_research_ai_text');
    loadingText.textContent = '웹사이트 데이터 수집중입니다.';
    document.getElementById('loading_bar_research_ai').style.display = 'block';
    
    console.log("******************");
    console.log(url);
    console.log(actionType);

    fetch('/api/website_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({website_url: url, type: actionType, llm_model: llm_model})
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('loading_bar_research_ai').style.display = 'none';
        document.getElementById('ai_invest_sec_applyWeb').disabled = false;
        document.getElementById('ai_invest_sec_applyWeb').style.opacity = "1";
        console.log(data.result);
        let transcript = data.result;
        contentArea.innerText = transcript;
        document.getElementById('webSiteHidden').setAttribute('data-transcript', transcript);
        toggleLayerPopup('website', url);
    })
    
    .catch(error => {
        console.error('Error:', error);
        alert("Website 데이터 추출에 실패했습니다.")
        document.getElementById('loading_bar_research_ai').style.display = 'none';
    });      
}


function readYoutubeScript(actionType = 'read') {
    const employeeId = document.getElementById('ai_invest_sec_employeeId').value;
    var url = document.getElementById('ai_invest_sec_youtubeUrl').value;
    if (employeeId.length !== 7) {
        alert("사번을 먼저 입력해주세요");
        return;
    }
    if (url.length < 5 || !url.startsWith('http') || !url.includes('youtu')) { //youtu.be 고려
        alert("URL을 정확하게 입력해주세요! (*http부터 입력)");
        return;
    }    
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
        document.getElementById('ai_invest_sec_applyYT').disabled = false;
        document.getElementById('ai_invest_sec_applyYT').style.opacity = "1";
        let transcript = data.transcript || 'Error loading data';
        // 줄바꿈 너무 안돼서 강제로 바꿔줌. 회사이름도 틀려서 바꿔줌
        transcript = transcript.replace(/(니다|세요|까요|겠죠|있죠|이죠)/g, '$1\n');
        transcript = transcript.replace(/미래[세셋]/g, '미래에셋')
        document.getElementById('youTubeHidden').setAttribute('data-transcript', transcript);
        contentArea.innerText = transcript;
        toggleLayerPopup('youtube', url);
    })
    
    .catch(error => {
        console.error('Error:', error);
        alert("Youtube 네트워킹에 실패했습니다.")
        document.getElementById('loading_bar_research_ai').style.display = 'none';
        document.getElementById('ai_invest_sec_applyYT').style.opacity = "0.5";
    });      
    //appendData("YouTube URL", url);
}

async function viewSavedFileContent(fileCollectionName) {
    const contentArea = document.getElementById('aiSecLayerPopupContent2');       
    try {
        var loadingText = document.getElementById('loading_research_ai_text');
        loadingText.textContent = 'File Read 중입니다.';
        document.getElementById('loading_bar_research_ai').style.display = 'block';

        const response = await fetch('/rag/ai-invest-view-file/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_collection_name: fileCollectionName })
        });
        if (!response.ok) {
            document.getElementById('loading_bar_research_ai').style.display = 'none';
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        document.getElementById('loading_bar_research_ai').style.display = 'none';        
        console.log("****")
        console.log(result.result.documents);
        contentArea.innerHTML = result.result.documents;
        toggleLayerPopup('file', fileCollectionName);        

    } catch (error) {
        console.error("Fetch error: " + error.message);
        document.getElementById('loading_bar_research_ai').style.display = 'none';  
        alert("데이터 조회 중 오류가 발생했습니다");
    }
}

function toggleLayerPopup(type, title) {
    var popupId, dialogWidth, titleId;    
    if(type === 'file'){
        popupId =  '#aiSecLayerPopup2';
        dialogWidth = 900
        const parts = title.split('_');
        const formattedName = parts[2];
        const fileType = parts[1].toUpperCase(); 
        var showTitle = formattedName+"."+fileType+" 파일 내용입니다"
        titleId = 'aisec_2_title';
        $('#' + titleId).text(showTitle);
    }else{
        popupId =  '#aiSecLayerPopup';
        dialogWidth = 800
        var showTitle = title + "의 추출 내용입니다"
        titleId = 'aisec_1_title'; 
        $('#' + titleId).text(showTitle);
    }
    $(popupId).dialog({
        dialogClass: 'research-dialog',
        title: showTitle, 
        modal: true,
        draggable: false,
        resizable: false,
        autoOpen: false,
        width: dialogWidth,
        height: 700,
        open: function() {
            $('.ui-widget-overlay').on('click', function() {
                $(popupId).dialog('close');
            });
            //타이틀 바꿔주기 
            $('#' + titleId).text(showTitle);
        }
    }).dialog('open');
}

function appendData(index, type, value, employeeId) {
    var container = document.getElementById('ai_invest_sec_appliedData');
    const displayValue = value !== "1" ? `${type} - ${value}` : type;
    if (container.innerHTML === "") {
        container.innerHTML += `<div class="header-with-button"><p>◎ MY DB 적용 데이터</p><button onclick="clearDB()" class="db-clear-btn">DB 클리어</button></div>`;
    }
    const formattedName = value.replace(/\s+/g, '_').replace(/\W/g, '').toLowerCase();
    const fileCollectionName = `${employeeId}_${type.toLowerCase()}_${formattedName}`;
    container.innerHTML += `<div class="ai_invest_data_box">
        <p class="ai_append_text">[나의 DB에 적용된 데이터 #${index}] ${displayValue}</p>
        ${['pdf', 'docx', 'doc'].includes(type.toLowerCase()) ? `<button onclick="viewSavedFileContent('${fileCollectionName}')" class="view-btn">내용보기</button>` : ''}
    </div>`;
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
    
    var loadingText = document.getElementById('loading_research_ai_text');
    loadingText.textContent = 'File Data 저장중입니다.';
    document.getElementById('loading_bar_research_ai').style.display = 'block';

    formData.append("employeeId", employeeId);
    fetch('/rag/ai-sec-upload/', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        document.getElementById('loading_bar_research_ai').style.display = 'none';
        alert("파일이 정상적으로 저장되었습니다.");
        aiSecViewMyDB();
    })
    .catch((error) => {
        console.error('Error:', error);
        document.getElementById('loading_bar_research_ai').style.display = 'none';
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
    //messageTextDiv.textContent = messageText;
    messageTextDiv.innerText = messageText;
    
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

async function layerPopupGptCall(requestType, sourceDivId) {
    const apiUrl = '/rag/layer_trans_sum/';
    console.log("aaaaaaaaaaaaaa");
    console.log(document.getElementById(sourceDivId).innerText);
    const data = {
        requestType: requestType,
        content: document.getElementById(sourceDivId).innerText
    };
    var loadingText = document.getElementById('loading_research_ai_text');
    loadingText.textContent = "데이터 Searching 중입니다.";
    var loadingBar = document.getElementById('loading_bar_research_ai');
    loadingBar.style.display = 'block';  // 로딩 바 표시
    loadingBar.style.position = 'fixed';  // 화면 중앙 고정
    loadingBar.style.top = '50%';         // 수직 중앙
    loadingBar.style.left = '50%';        // 수평 중앙
    loadingBar.style.transform = 'translate(-50%, -50%)'; // 정확한 중앙    
    loadingBar.style.transform = 'translate(-50%, -50%)'; // 정확한 중앙
    loadingBar.style.zIndex = '9999';  
    try {
        // Fetch API를 사용하여 POST 요청 전송
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const responseData = await response.json();
        console.log('Server response:', responseData);
        document.getElementById('loading_bar_research_ai').style.display = 'none';   
        document.getElementById(sourceDivId).innerText = responseData.result;

    } catch (error) {
        console.error('Error during fetch:', error);
        document.getElementById('loading_bar_research_ai').style.display = 'none';   
    }
}
//******************************** 3RD GNB::  AI 투자비서 Ends **********************************************//          