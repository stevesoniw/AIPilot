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
        this.unhighlight(e);
        let dt = e.dataTransfer;
        let files = dt.files;
        this.handleFiles(files);
        this.fileList.scrollTo({ top: this.fileList.scrollHeight });
    }

    handleFiles(files) {
        console.log("Handling files:", files);
        files = [...files];
        files.forEach(file => this.previewFile(file));
    }

    previewFile(file) {
        let fileDOM = this.renderFile(file);
        if (fileDOM) {
            this.fileList.appendChild(fileDOM); // Add the file preview to the fileList
            this.fileList.style.display = 'block'; // Make sure fileList is visible
            submitFiles(); // This call can be adjusted based on your needs
        } else {
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

/* 파일 업로드 끝 */

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
            result.files_metadata.forEach((meta, index) => {
                if (fileElements[index]) {
                    fileElements[index].setAttribute('data-file-id', meta.file_id);
                }
            });
        } else {
            console.error("Failed to upload files. Status:", response.status);
            if (response.headers.get("Content-Type")?.includes("application/json")) {
                console.error("Error details:", await response.json());
            }
        }
    } catch (error) {
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

function getAnswerUsingPrompt(selectedPrompt){
    const fileElements = document.querySelectorAll('#showfiles .file');
    
    if (fileElements.length === 0) {
        alert('PDF 파일을 업로드 후에 선택해주세요!');
        return;
    }
    //정수로 변환필요 (python 서버에 int 선언되어있음)
    const fileIds = Array.from(fileElements).map(fileElement => parseInt(fileElement.getAttribute('data-file-id')));
    console.log(selectedPrompt);
    console.log(fileIds);
    document.getElementById('loading_bar_ragprompt').style.display = 'block';

    fetch(`/rag/answer-from-prompt`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt_option: selectedPrompt,
            file_ids: fileIds
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Server response:', data);
        document.getElementById('loading_bar_ragprompt').style.display = 'none';
        const answerWrap = document.querySelector('.answer-wrap');
        answerWrap.innerText = data;  

        const selectedOptionText = document.querySelector('#promptSelect option:checked').text;
        document.querySelector('.question-wrap').textContent = selectedOptionText;
    })
    .catch(error => {
        document.getElementById('loading_bar_ragprompt').style.display = 'none';        
        console.error('getAnswerUsingPrompt error:', error);
    });
}

/* 툴팁 시작 */
function jTooltip(){
    $('.chat-info.-right-ver').tooltip({
        position: {
            my: 'left bottom-10',
            at: 'left top',
            using: function(position, feedback){
                $(this).css(position);
                $('<div>').addClass('arrow').addClass(feedback.vertical).addClass(feedback.horizontal).appendTo(this);
            }
        },
        content: function(){
            return $(this).attr('title');
        },
        show: {
            duration: 100
        }
    });
}
/* 툴팁 끝 */

$(document).ready(function(){
    guideTab();

    $('#accordion').accordion({
        collapsible: true,
        animate: 300,
        active: 2,
        heightStyle: 'content',
        classes: {
            'ui-accordion':'nav-acc',
            'ui-accordion-header': 'nav-acc-header',
            'ui-accordion-content': 'nav-acc-content'
        },
        icons: {
            header:'nav-acc-ic',
            activeHeader:'nav-acc-ic-active'
        },
        beforeActivate: function(){
            // 활성화되기 전에 코드를 실행합니다.
            console.log('활성화되기 전에 코드를 실행합니다.');
        },
        activate: function(){
            // 활성화된 후에 코드를 실행합니다.
            console.log('활성화된 후에 코드를 실행합니다.');
        }
    });

    jTooltip();

});
//******************************** 3RD GNB::  리서치RAG Ends   ***********************************************//   