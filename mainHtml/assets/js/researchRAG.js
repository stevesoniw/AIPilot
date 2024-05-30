//******************************** 3RD GNB::  리서치 PDF Starts **********************************************//
/* 사용자 ID를 저장할 변수 */
let userId = null;  
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
                        // 모든 파일이 삭제되면 userId를 지움
                        if (this.fileList.childElementCount === 0) {
                            userId = null;
                        }                        
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
        fetch(`/file/${userId}/${fileId}`, {  
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            console.log("Server response after deletion:", data.message);
            console.log(data.files_metadata);
            createOptions(data.files_metadata.length);
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
            //파일 한번 안 올리고 안 올렸을 때 에러잡기
            if (files.length === 0) {
                alert("파일을 업로드하지 않았습니다");
            }
            else {
                element.textContent = '리포트 업로드 중입니다'; 
                loading.style.display = 'block';
            }

        }        
        if (files.length != 0) {
            console.log("Handling files are:", files);
            files = [...files];
            this.previewFile(files);
        }
    }

    previewFile(files) {
        var flag = 0;
        for (let i = 0; i < files.length; i++) {
            let fileDOM = this.renderFile(files[i]);
            if (fileDOM) {
                this.fileList.appendChild(fileDOM); // Add the file preview to the fileList
                this.fileList.style.display = 'block'; // Make sure fileList is visible
                flag = 1;
                
            } else {
                document.getElementById('loading_bar_ragprompt').style.display = 'none';
                console.log("File verification failed");
                
            }
        }
        // console.log(this.fileList);

        if( flag == 1 ) {
            setTimeout(submitFiles, 100);}
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
        const fileTitles = document.getElementsByClassName('file-tit');
        if (fileTitles) {
            for (let i = 0; i < fileTitles.length; i++) {
                // 현재 요소의 텍스트 내용을 가져옴
                const text = fileTitles[i].textContent;
                
                // 만약 텍스트에 'A.pdf'가 포함되어 있다면
                if (text.includes(file.name)) {
                    alert("이미 추가한 파일입니다. 다시 업로드해주세요.");
                    // 실행을 하지 않고 함수를 종료
                    return null;
                }     
            }
        }

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
// 파일 개수에 따라 프롬프트 예시 바꿔주는 함수
const createOptions = (numFiles) => {
    const select = document.getElementById('promptSelect');

    // Clear existing options
    select.innerHTML = '';
    select.className = "research-select";

    if (numFiles > 1) {
        // More than 1 file: options D, E, F
        const options = [["default", "질문이 떠오르지 않으신다면, 다음 예시 질문들을 사용해보세요."],
        ["A", "리포트들을 보고 해당 기업의 Bull, Bear 포인트들을 사업부 별로 정리해서 표로 보여줘."],
        ["B", "각 리포트에서 공통적으로 언급되는 주제/키워드를 몇가지 선정하고, 의견이 일치하는 부분과 일치하지 않는 부분을 정리해줘.\
        하위 문장의 구분은 숫자가 아닌 '•'으로 구분해주고 개별 문장은 한문장씩 끊어서 답변하되 '-합니다', '-입니다'는 빼고 문장을 만들어줘."],
        ["C", "각 리포트들에서 전문용어/약어를 사용한 경우 이에 대한 설명을 추가해줘.\
        앞으로 용어를 설명할 때 '-입니다', '-됩니다'는 빼고 간결하게 대답해줘.\
        답변의 시작은 '용어 설명'으로 하고, 용어들은 1,2,3 순서를 매겨서 알려줘.\
        정리할 때, 재무적 용어 (ex. QoQ, YoY)나 리포트용 약어는 제외하고 정리해줘."]]
        options.forEach((option) => {
            const optionElement = document.createElement('option');
            optionElement.value = option[0];
            optionElement.textContent = option[1];
            select.appendChild(optionElement);
        });
    } else {
        // 1 file: options A, B, C
        const options = [["default", "질문이 떠오르지 않으신다면, 다음 예시 질문들을 사용해보세요."],
            ["A", "1. 리포트를 읽고 해당 기업의 Bull, Bear 포인트를 사업분야 별로 표로 정리해줘"],
            ["B", "2. 리포트를 읽고 해당 기업의 이번 분기 실적이 어땠는지 알려줘. 뭘 근거로 리포트에서 그렇게 판단했는지도 알려줘"],
            ["C", "3. 리포트에 쓰인 전문 용어가 있으면 설명해줘. 이 기업에서 하는 사업과 관련된 용어들 중에 생소한 것들은 꼭 알려줘"]]
        options.forEach((option) => {
            const optionElement = document.createElement('option');
            optionElement.value = option[0];
            optionElement.textContent = option[1];
            select.appendChild(optionElement);
        });
    }
};
/* 파일 파이썬 서버로 올리기 */
async function submitFiles() {
    const form = document.getElementById('file-upload-form');
    // console.log(form.innerHTML);
    const formData = new FormData(form);
    if (userId) {
        formData.append('user_id', userId);  // 기존 사용자 ID를 추가
    }    
    try {
        const response = await fetch(`/rag/prompt-pdf-upload`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            userId = result.user_id;  
            //console.log("***************************************");
            console.log("userId=",userId);
            //console.log("***************************************");
            createOptions(result.files_metadata.length);
            console.log("Files uploaded successfully:", result);
            const fileElements = document.querySelectorAll('#showfiles .file'); 
            document.getElementById('loading_bar_ragprompt').style.display = 'none';
            result.files_metadata.forEach((meta, index) => {
                if (fileElements[index]) {
                    fileElements[index].setAttribute('data-file-id', meta.file_id);
                    //console.log("File Metadata Entry:");
                    //console.log(meta);
                    //console.log("File ID:", meta.file_id);
                }
            });
        } else {
            alert("파일을 읽을 수 없습니다. 파일이 암호화되었는지 확인해주세요.");
            // 암호화된 파일일 경우 pypdf로 읽을 수 없어 500 에러가 남. 
            // 에러가 났을 시 해당 파일을 화면 단에서 지운다]
            // 멀티 파일 올리고 하나가 에러 나면 모든 파일을 지움.
            for (let pair of formData.entries()) {
                // console.log(pair);
                if (pair[0] === "files") {
                    // console.log(pair[1]);
                    const invalidFile = pair[1].name;
                    // 모든 file 클래스 요소 선택
                    const fileElements = document.querySelectorAll('.file');

                    // 각 파일 요소에 대해 반복
                    fileElements.forEach(fileElement => {
                        // 파일 제목 요소 선택
                        const fileTitleElement = fileElement.querySelector('.file-tit');
                        
                        // 파일 제목 요소가 존재하는지 확인
                        if (fileTitleElement) {
                            // 파일 이름을 가져옴
                            const fileName = fileTitleElement.textContent.trim();

                            // 파일 이름이 "name.pdf"인 경우 파일 요소 삭제
                            if (fileName === invalidFile) {
                                fileElement.remove();
                            }
                        }
                    });

                }
            }
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

//Helper function

function copyText(button) {
    var answerWrap = button.closest(".answer-wrap");
        
    if (answerWrap) {
        var answerTxt = answerWrap.querySelector(".answer-txt");
        if (answerTxt) {
            var textToCopy = answerTxt.textContent.trim();
            var tempTextArea = document.createElement('textarea');
            tempTextArea.value = textToCopy;
        
            // Make the textarea invisible
            tempTextArea.style.position = 'fixed';
            tempTextArea.style.top = 0;
            tempTextArea.style.left = 0;
            tempTextArea.style.opacity = 0;
        
            // Append the textarea to the body
            document.body.appendChild(tempTextArea);
        
            // Select the textarea's content
            tempTextArea.select();
        
            // Execute the browser's built-in copy command
            document.execCommand('copy');
        
            // Remove the textarea from the DOM
            document.body.removeChild(tempTextArea);
        
            alert('텍스트가 복사되었습니다.');


            // var textToCopy = answerTxt.textContent.trim();
            // navigator.clipboard.writeText(textToCopy)
            //     .then(function() {
            //         alert("텍스트가 성공적으로 복사되었습니다.");
            //     })
            //     .catch(function(error) {
            //         console.error("텍스트 복사 중 오류가 발생하였습니다:", error);
            //     });

        } else {
            console.error(".answer-txt를 찾을 수 없습니다.");
        }
    } else {
        console.error(".answer-wrap을 찾을 수 없습니다.");
    }

}

function captureWithBackgroundColor(element) {
    // Set background color to white temporarily
    element.style.backgroundColor = "white";

    // Capture the element
    return domtoimage.toPng(element)
        .then(function (dataUrl) {
            // Reset background color to transparent
            element.style.backgroundColor = "transparent";
            return dataUrl;
        })
        .catch(function (error) {
            console.error('Error capturing element:', error);
            // Reset background color to transparent in case of error
            element.style.backgroundColor = "transparent";
            throw error; // rethrow the error
        });
}

function saveAsImage(button) {
    // var answerWrap = button.closest(".answer-wrap");
        
    // if (answerWrap) {
    //     var answerTxt = answerWrap.querySelector(".answer-txt");
    //     if (answerTxt) {
    //         // HTML 캔버스 생성
    //         html2canvas(answerTxt).then(function(canvas) {
    //             // 캔버스를 이미지 데이터 URL로 변환
    //             var imageData = canvas.toDataURL("image/png");
                
    //             // 이미지 다운로드 링크 생성
    //             var downloadLink = document.createElement("a");
    //             downloadLink.href = imageData;
    //             downloadLink.download = "answer_image.png";
                
    //             // 링크를 클릭하여 이미지 다운로드
    //             downloadLink.click();
    //         });
    //     } else {
    //     console.error(".answer-txt를 찾을 수 없습니다.");
    //     }
    // } else {
    //     console.error("부모 요소인 .answer-wrap을 찾을 수 없습니다.");
    // }
    var answerWrap = button.closest(".answer-wrap");
        
    if (answerWrap) {
        var answerTxt = answerWrap.querySelector(".answer-txt");
        if (answerTxt) {
            captureWithBackgroundColor(answerTxt).then(function(dataUrl) {
                // Create download link
                var downloadLink = document.createElement("a");
                downloadLink.href = dataUrl;
                // downloadedImg.crossOrigin = "anonymous";
                downloadLink.download = "answer_image.png";

                // Click the link to trigger download
                downloadLink.click();
            })
            .catch(function(error) {
                console.error("이미지 다운로드 중 오류가 발생하였습니다:", error);
            });
            } else {
                    console.error(".answer-txt를 찾을 수 없습니다.");
                    }

    } else {
        console.error("부모 요소인 .answer-wrap을 찾을 수 없습니다.");
    }

}

let questionCounter = 0;
//Prompt Select 창 클릭 시 서버쪽 답변 요청함수 
async function getAnswerUsingPrompt(selectedPrompt){
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

    if (questionCounter === 0) {
        const talkListWrap = document.querySelector('.chat-list-wrap');
        talkListWrap.innerHTML = ""; //예시 지워

    }
    //다음부턴 이전답변 지우지마
    questionCounter++; 

    //정수로 변환필요 (python 서버에 int 선언되어있음)
    const fileIds = Array.from(fileElements).map(fileElement => fileElement.getAttribute('data-file-id'));
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

    //Answer 클라스 생성
    const answerWrap = document.createElement('div');
    answerWrap.className = 'answer-wrap';
    talkListWrap.appendChild(answerWrap);
        
    
    // 버튼 클라스 생성
    // 새로운 div 요소 생성
    var newDiv = document.createElement("div");
    newDiv.classList.add("answer-btn-wrap"); // div에 버튼 클래스 추가
    
    // 내부 HTML 코드 설정
    newDiv.innerHTML = `
    <button type="button" class="answer-btn answer-copy" onclick=copyText(this)>copy</button>
    <button type="button" class="answer-btn answer-save" onclick="saveAsImage(this)">save</button>
    `;
    
    answerWrap.appendChild(newDiv);
    
    var textDiv = document.createElement("div");
    textDiv.classList.add("answer-txt"); // div에 answer-txt 클라스 추가
    textDiv.style.padding = "30px 10px 10px 10px"; //버튼 아래로 답이 나오게 패딩 세팅
    answerWrap.appendChild(textDiv);

    //gpt에 프롬프트 날리기
    textDiv.innerHTML = '<p>리포트를 읽고 있습니다... (리포트 개수가 많을수록 시간이 더 걸릴 수 있습니다)</p>'
    talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' })
    const response = await fetch('/rag/answer-from-prompt',{
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,  
                prompt_option: selectedPrompt,
                file_ids: fileIds.map(String), 
                tool_used: checkboxValue
            })}
    );
    console.log(response);
    textDiv.innerHTML = '';

    converter = new showdown.Converter(),
    converter.setOption('tables', true) //테이블 파싱하게 세팅
     //markdown --> HTML
    var reader = response.body.getReader();
    var decoder = new TextDecoder('utf-8');




    reader.read().then(function processResult(result) {    
        if (result.done) {
            converter = new showdown.Converter({smoothLivePreview: true}),
            converter.setOption('tables', true) //테이블 파싱하게 세팅
            html = converter.makeHtml(textDiv.innerHTML); //markdown --> HTML
            console.log(html);
            textDiv.innerHTML = html;
            talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });

            // talkListWrap.scrollIntoView({ behavior: "smooth", block: "end"});
            // window.scrollTo(0, answerWrap.scrollHeight);

            
            customScrollTo('top');
            return;}

        let token = decoder.decode(result.value);
        textDiv.innerHTML += token 
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
    console.log(questionCounter);
    const fileElements = document.querySelectorAll('#showfiles .file');
    const talkListWrap = document.querySelector('.chat-list-wrap');
    if (fileElements.length === 0) {
        alert('PDF 파일을 먼저 업로드 후 질문해주세요\n(※해당 채팅은 PDF 내용을 바탕으로만 답변합니다.)');
        return;
    }

    if (questionCounter === 0) {
        const talkListWrap = document.querySelector('.chat-list-wrap');
        talkListWrap.innerHTML = ""; //예시 지워

    }
    //다음부턴 이전답변 지우지마
    questionCounter++;
    displayQuestion(question);
 
    
    const fileIds = Array.from(fileElements).map(fileElement => parseInt(fileElement.getAttribute('data-file-id')));
    // 체크박스 value 체킹
    let checkboxValue = null;
    if (document.getElementById('researchGPT4').checked) {
        checkboxValue = document.getElementById('researchGPT4').value;
    } else if (document.getElementById('researchLama3').checked) {
        checkboxValue = document.getElementById('researchLama3').value;
    }

    //Answer 클라스 생성
    const answerWrap = document.createElement('div');
    answerWrap.className = 'answer-wrap';
    talkListWrap.appendChild(answerWrap);
    // document.querySelector('.answer-wrap').innerHTML = "";
    // 버튼 클라스 생성
    // 새로운 div 요소 생성
    var newDiv = document.createElement("div");
    newDiv.classList.add("answer-btn-wrap"); // div에 버튼 클래스 추가
    
    // 내부 HTML 코드 설정
    newDiv.innerHTML = `
    <button type="button" class="answer-btn answer-copy" onclick=copyText(this)>copy</button>
    <button type="button" class="answer-btn answer-save" onclick="saveAsImage(this)">save</button>
    `;
    
    answerWrap.appendChild(newDiv);
    
    var textDiv = document.createElement("div");
    textDiv.classList.add("answer-txt"); // div에 answer-txt 클라스 추가
    textDiv.style.padding = "30px 10px 10px 10px"; //버튼 아래로 답이 나오게 패딩 세팅
    answerWrap.appendChild(textDiv);

    textDiv.innerHTML = '<p>리포트를 읽고 있습니다... (리포트 개수가 많을수록 시간이 더 걸릴 수 있습니다)</p>'
    talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' })

    const response = await fetch(`/rag/answer-from-prompt`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,  
            question: question,
            file_ids: fileIds.map(String), 
            tool_used: checkboxValue
        })
    })
    console.log(response);
    textDiv.innerHTML = ''; 
    converter = new showdown.Converter(),
    converter.setOption('tables', true) //테이블 파싱하게 세팅
     //markdown --> HTML
    var reader = response.body.getReader();
    var decoder = new TextDecoder('utf-8');



    reader.read().then(function processResult(result) {    
        if (result.done) {
            converter = new showdown.Converter({smoothLivePreview: true}),
            converter.setOption('tables', true) //테이블 파싱하게 세팅
            html = converter.makeHtml(textDiv.innerHTML); //markdown --> HTML
            console.log(html);
            textDiv.innerHTML = html;
            talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });

            // talkListWrap.scrollIntoView({ behavior: "smooth", block: "end"});
            // window.scrollTo(0, answerWrap.scrollHeight);

            
            // customScrollTo('bottom');
            return;}

        let token = decoder.decode(result.value);
        textDiv.innerHTML += token 
        talkListWrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
        return reader.read().then(processResult);
    });

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