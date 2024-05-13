//******************************** 3RD GNB::  리서치 PDF Starts **********************************************//
/* 파일 업로드 시작 */
class DropFile {
    constructor(dropAreaId, fileListId) {
        this.dropArea = document.getElementById(dropAreaId);
        this.fileList = document.getElementById(fileListId);
        this.init();
        this.attachDeleteHandler(); 
    }

    init() {
        this.dropArea.addEventListener("dragenter", this.highlight.bind(this), false);
        this.dropArea.addEventListener("dragover", this.highlight.bind(this), false);
        this.dropArea.addEventListener("dragleave", this.unhighlight.bind(this), false);
        this.dropArea.addEventListener("drop", this.handleDrop.bind(this), false);
    }

    attachDeleteHandler() {
        // Listen for clicks on the fileList container
        this.fileList.addEventListener('click', (event) => {
            console.log("Clicked within fileList:", event.target);
            const deleteButton = event.target.closest('.upload-delete');
            if (deleteButton) {
                // Confirm the delete button was targeted
                console.log("Delete button was clicked:", deleteButton);

                const fileElement = deleteButton.closest('.file');
                if (fileElement) {
                    // Confirm the file DOM is correctly identified
                    console.log("File element found for deletion:", fileElement);

                    const fileId = fileElement.getAttribute('data-file-id');
                    if (fileId) {
                        console.log("File ID found:", fileId);
                        this.handleFileDeletion(fileId);
                        fileElement.remove(); // This removes the file DOM element
                        console.log("File element removed from DOM.");
                    } else {
                        console.log("No file ID found on the element to delete.");
                    }
                } else {
                    console.log("No file element found surrounding the delete button.");
                }
            }
        });
    }

    updateMetainfoAfterDeletion(fileId) {
        const metainfo = document.getElementById('metainfo');
        const fileMetadataDiv = document.querySelector(`div[data-file-id="${fileId}"]`);
        if (fileMetadataDiv) {
            fileMetadataDiv.remove();
        }
    }  

    handleFileDeletion(fileId) {
        fetch(`/file/${fileId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            console.log("Server response after deletion:", data.message);
            this.updateMetainfoAfterDeletion(fileId);
            //storeFileMetadata(data.files_metadata);
        })
        .catch(error => console.error('Error deleting file:', error));
    } 
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight(e) {
        this.preventDefaults(e);
        this.dropArea.classList.add("highlight");
    }

    unhighlight(e) {
        this.preventDefaults(e);
        this.dropArea.classList.remove("highlight");
    }

    handleDrop(e) {
        this.preventDefaults(e);
        let dt = e.dataTransfer;
        let files = dt.files;
        console.log("Dropped files:", files); // 드롭된 파일 로그 출력
        if (files.length > 0) { 
            this.handleFiles(files);
            this.updateInputFiles(files); 
            this.fileList.scrollTo({ top: this.fileList.scrollHeight });
        } else {
            console.error("No files dropped");
        }
    }

    updateInputFiles(files) {
        const fileInput = document.getElementById('chooseFile');
        const dataTransfer = new DataTransfer(); // 새 DataTransfer 객체 생성
        for (let file of files) {
            console.log("filesssssssss:", file);
            dataTransfer.items.add(file); // 파일을 DataTransfer 아이템에 추가
        }
        fileInput.files = dataTransfer.files; // input 요소의 files 속성 업데이트
    }

    handleFiles(files) {
        var element = document.getElementById('loading-text-ragprompt'); 
        var loading = document.getElementById('loading_bar_ragprompt');
        if (element && loading) {
          element.textContent = '리포트 업로드 중입니다'; 
          loading.style.display = 'block';
        }        
        console.log("Handling files are:", files);
        files = [...files];
        files.forEach(file => this.previewFile(file));
    }

    previewFile(file) {
        let fileDOM = this.renderFile(file);
        if (fileDOM) {
            this.fileList.appendChild(fileDOM); // Add the file preview to the fileList
            this.fileList.style.display = 'block'; // Make sure fileList is visible
            setTimeout(submitFiles, 100); 
        } else {
            document.getElementById('loading_bar_ragprompt').style.display = 'none';
            console.log("File verification failed");
        }
    }

    renderFile(file) {
        const maxSize = 30 * 1024 * 1024; // 30MB
        if (file.size > maxSize) {
            console.log("파일 크기 검증 실패");
            alert("파일 크기가 너무 큽니다. 30MB 이하의 파일만 업로드 가능합니다.");
            return null;
        }
    
        const validExtensions = ['pdf'];
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!validExtensions.includes(fileExtension)) {
            console.log("파일 확장자 검증 실패: " + fileExtension);
            alert("지원하지 않는 파일 형식입니다. PDF 파일만 업로드 가능합니다.");
            return null;
        }
    
        // 파일 정보를 담을 DOM 요소 생성 및 반환
        let fileDOM = document.createElement("div");
        fileDOM.className = "file";
        fileDOM.innerHTML = `
            <div class="thumbnail">
            <img src="/static/assets/images/upload-file-ic.png" alt="파일타입 이미지" class="image">
            </div>
            <div class="details">
            <div class="file-tit">
                ${file.name}
            </div>
            <div class="progress">
                <div class="bar"></div>
            </div>
            <div class="status">
                <span class="percent">100% done</span>
            </div>
            </div>
            <a title="첨부파일 삭제" class="upload-delete"><span>첨부파일 삭제</span></a>
        `;
        return fileDOM;
    }
}
//const dropFile = new DropFile("drop-file", "files");

/* 실제 파일 업로드 Class 끝 */

/* 파일 파이썬 서버로 올리기 */
async function submitFiles() {
    const form = document.getElementById('file-upload-form');
    const formData = new FormData(form);
    try {
        const response = await fetch(`/rag/prompt-pdf-upload`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            console.log("Files uploaded successfully:", result);
            const fileElements = document.querySelectorAll('#showfiles .file'); 
            document.getElementById('loading_bar_ragprompt').style.display = 'none';
            result.files_metadata.forEach((meta, index) => {
                if (fileElements[index]) {
                    fileElements[index].setAttribute('data-file-id', meta.file_id);
                }
            });
        } else {
            console.error("Failed to upload files. Status:", response.status);
            document.getElementById('loading_bar_ragprompt').style.display = 'none';
            if (response.headers.get("Content-Type")?.includes("application/json")) {
                console.error("Error details:", await response.json());
            }
        }
    } catch (error) {
        document.getElementById('loading_bar_ragprompt').style.display = 'none';
        console.error("Error uploading files:", error);
    }
}


function storeFileMetadata(filesMetadata) {
    const filesContainer = document.getElementById('metainfo');
    filesContainer.innerHTML = '';

    filesMetadata.forEach(file => {
        const fileEntry = document.createElement('div');
        fileEntry.className = 'file-metadata';
        fileEntry.setAttribute('data-file-id', file.file_id);  
        fileEntry.innerHTML = `
            <div>
                File ID: ${file.file_id}, Name: ${file.file_name}
            </div>
        `;
        filesContainer.appendChild(fileEntry);
    });
}

let questionCounter = 0;
//Prompt Select 창 클릭 시 서버쪽 답변 요청함수 
async function getAnswerUsingPrompt(selectedPrompt){
    if (questionCounter === 0) {
        const talkListWrap = document.querySelector('.chat-list-wrap');
        talkListWrap.innerHTML = ""; //예시 지워

    }
    //다음부턴 이전답변 지우지마
    questionCounter++; 
    const fileElements = document.querySelectorAll('#showfiles .file');
    console.log("selectedPrompt=", selectedPrompt);
    if (selectedPrompt === 'default') {
        console.log("Default prompt selected - no action taken.");
        return;  
    }
    if (fileElements.length === 0) {
        alert('PDF 파일을 업로드 후에 선택해주세요!');
        return;
    }
    //정수로 변환필요 (python 서버에 int 선언되어있음)
    const fileIds = Array.from(fileElements).map(fileElement => parseInt(fileElement.getAttribute('data-file-id')));
    console.log(selectedPrompt);
    console.log(fileIds);
    var element = document.getElementById('loading-text-ragprompt'); 
    var loading = document.getElementById('loading_bar_ragprompt');
    if (element && loading) {
      element.textContent = '리포트 분석중 입니다'; 
    //   loading.style.display = 'block';
    }        
    // 체크박스 value 체킹
    let checkboxValue = null;
    if (document.getElementById('researchGPT4').checked) {
        checkboxValue = document.getElementById('researchGPT4').value;
    } else if (document.getElementById('researchLama3').checked) {
        checkboxValue = document.getElementById('researchLama3').value;
    }
    //Question-wrap 클라스 새로 생성
    const questionWrap = document.createElement('div');
    questionWrap.className = 'question-wrap prompt-ver';
    const talkListWrap = document.querySelector('.chat-list-wrap');
    // prompt 가져오고 클라스에 prompt를 집어넣는다
    const selectedOptionText = document.querySelector('#promptSelect option:checked').text;
    var question = document.createTextNode(selectedOptionText)
    questionWrap.appendChild(question); 
    talkListWrap.appendChild(questionWrap);

    //gpt에 프롬프트 날리기
    const response = await fetch('/rag/answer-from-prompt',{
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt_option: selectedPrompt,
                file_ids: fileIds,
                tool_used: checkboxValue
            })}
    );
    console.log(response);

    converter = new showdown.Converter(),
    converter.setOption('tables', true) //테이블 파싱하게 세팅
     //markdown --> HTML
    var reader = response.body.getReader();
    var decoder = new TextDecoder('utf-8');

    //Answer 클라스 생성
    const answerWrap = document.createElement('div');
    answerWrap.className = 'answer-wrap';
    talkListWrap.appendChild(answerWrap);
    // document.querySelector('.answer-wrap').innerHTML = "";

    reader.read().then(function processResult(result) {    
        if (result.done) {
            converter = new showdown.Converter({smoothLivePreview: true}),
            converter.setOption('tables', true) //테이블 파싱하게 세팅
            html = converter.makeHtml(answerWrap.innerHTML); //markdown --> HTML
            console.log(html);
            answerWrap.innerHTML = html;
            talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });

            // talkListWrap.scrollIntoView({ behavior: "smooth", block: "end"});
            // window.scrollTo(0, answerWrap.scrollHeight);

            
            customScrollTo('top');
            return;}

        let token = decoder.decode(result.value);
        
        answerWrap.innerHTML += token 

        talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });

        return reader.read().then(processResult);
    });


}


/* 채팅 창 컨트롤 하기 */
function processInput() {
    const inputField = document.getElementById('ragchat'); 
    const userInput = inputField.value.trim();
    if (userInput) {
        sendChatRequest(userInput);
        inputField.value = ''; 
    }
}

function displayQuestion(question) {
    const questionWrap = document.createElement('div');
    const talkListWrap = document.querySelector('.chat-list-wrap');
    questionWrap.className = 'question-wrap';
    questionWrap.textContent = question;
    talkListWrap.appendChild(questionWrap);
    // talkListWrap.style.display = 'flex'; // 보이게하는거
}

function customScrollTo(position) {
    if (position === 'bottom') {
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
    } else if (position === 'top') {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
}

async function sendChatRequest(question) {
    const fileElements = document.querySelectorAll('#showfiles .file');
    const talkListWrap = document.querySelector('.chat-list-wrap');
    if (fileElements.length === 0) {
        alert('PDF 파일을 먼저 업로드 후 질문해주세요\n(※해당 채팅은 PDF 내용을 바탕으로만 답변합니다.)');
        return;
    }
    displayQuestion(question);
    const fileIds = Array.from(fileElements).map(fileElement => parseInt(fileElement.getAttribute('data-file-id')));
    // 체크박스 value 체킹
    let checkboxValue = null;
    if (document.getElementById('researchGPT4').checked) {
        checkboxValue = document.getElementById('researchGPT4').value;
    } else if (document.getElementById('researchLama3').checked) {
        checkboxValue = document.getElementById('researchLama3').value;
    }

    const response = await fetch(`/rag/answer-from-prompt`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            question: question,
            file_ids: fileIds,
            tool_used: checkboxValue
        })
    })
    console.log(response);
    converter = new showdown.Converter(),
    converter.setOption('tables', true) //테이블 파싱하게 세팅
     //markdown --> HTML
    var reader = response.body.getReader();
    var decoder = new TextDecoder('utf-8');

    //Answer 클라스 생성
    const answerWrap = document.createElement('div');
    answerWrap.className = 'answer-wrap';
    talkListWrap.appendChild(answerWrap);
    // document.querySelector('.answer-wrap').innerHTML = "";

    reader.read().then(function processResult(result) {    
        if (result.done) {
            converter = new showdown.Converter({smoothLivePreview: true}),
            converter.setOption('tables', true) //테이블 파싱하게 세팅
            html = converter.makeHtml(answerWrap.innerHTML); //markdown --> HTML
            console.log(html);
            answerWrap.innerHTML = html;
            talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });

            // talkListWrap.scrollIntoView({ behavior: "smooth", block: "end"});
            // window.scrollTo(0, answerWrap.scrollHeight);

            
            // customScrollTo('bottom');
            return;}

        let token = decoder.decode(result.value);
        
        answerWrap.innerHTML += token 

        talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });

        return reader.read().then(processResult);
    });
    // document.getElementById('loading_bar_ragprompt').style.display = 'block';

    // fetch(`/rag/answer-from-prompt`, {
    //     method: 'POST',
    //     headers: {
    //         'Content-Type': 'application/json'
    //     },
    //     body: JSON.stringify({
    //         question: question,
    //         file_ids: fileIds,
    //         tool_used: checkboxValue
    //     })
    // })
    // .then(response => response.json())
    // .then(data => {
    //     document.getElementById('loading_bar_ragprompt').style.display = 'none';
    //     displayAnswer(data);
    // })
    // .catch(error => {
    //     console.error('Error fetching the answer:', error);
    //     document.getElementById('loading_bar_ragprompt').style.display = 'none';
    //     displayAnswer('API 서버가 불안정해요. 다시 질문해주세요!');
    // })
    // .finally(() => {
    //     document.getElementById('loading_bar_ragprompt').style.display = 'none';
    // });
};

function displayAnswer(answer) {
    const answerWrap = document.createElement('div');
    answerWrap.className = 'answer-wrap';
    answerWrap.innerHTML = answer; 
    const talkListWrap = document.querySelector('.talk-list-wrap');
    talkListWrap.appendChild(answerWrap);
    answerWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function textareaTxt(){
    $('.chat-ipt').focus(function(){
        $('.chat-ipt-wrap label').hide();
    });
    $('.chat-ipt').blur(function(){
        $('.chat-ipt-wrap label').show();
    });
}

//******************************** 3RD GNB::  리서치RAG Ends   ***********************************************//   