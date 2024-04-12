//******************************** 3RD GNB::  리서치 PDF Starts **********************************************//
/* 파일 업로드 시작 */
function DropFile(dropAreaId, fileListId) {
    let dropArea = document.getElementById(dropAreaId);
    let fileList = document.getElementById(fileListId);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        preventDefaults(e);
        dropArea.classList.add("highlight");
    }

    function unhighlight(e) {
        preventDefaults(e);
        dropArea.classList.remove("highlight");
    }

    function handleDrop(e) {
        unhighlight(e);
        let dt = e.dataTransfer;
        let files = dt.files;

        handleFiles(files);

        const fileList = document.getElementById(fileListId);
        if (fileList) {
        fileList.scrollTo({ top: fileList.scrollHeight });
        }
    }

    function handleFiles(files) {
        files = [...files];
        files.forEach(previewFile);

        /* 첨부파일 삭제 */
        $('.upload-delete').click(function(){
            // $('#chooseFile').val('');
            $(this).parent('.file').remove();
        });
        /* 첨부파일 삭제 */
    }

    function previewFile(file) {
        const fileDOM = renderFile(file); // renderFile에서 DOM 요소 또는 null 반환
        // fileDOM이 null이 아닌 경우에만 appendChild 호출
        if (fileDOM !== null) {
            fileList.appendChild(renderFile(file));
        } else {
            // null인 경우, 적절한 처리를 여기서 진행한다
            console.log("파일 검증 실패: 올바른 파일을 첨부해주세요.");
        }
    }

    function renderFile(file) {
        // 파일 크기 체크 (30MB 이하만 허용)
        const maxSize = 30 * 1024 * 1024; // 30MB
        if (file.size > maxSize) {
            alert("파일 크기가 너무 큽니다. 30MB 이하의 파일만 업로드 가능합니다.");
            return null; // 혹은 적절한 에러 처리
        }
        
        // 파일 확장자 체크 (PDF만 허용)
        const validExtensions = ['pdf'];
        // 파일 이름에서 마지막 '.'을 기준으로 확장자 추출
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!validExtensions.includes(fileExtension)) {
            alert("지원하지 않는 파일 형식입니다. PDF 파일만 업로드 가능합니다.");
            return null; // 혹은 적절한 에러 처리
        }

        // 파일 정보를 담을 DOM 요소 생성
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
        return fileDOM; // 조건을 모두 만족하면 DOM요소 반환
    }

    dropArea.addEventListener("dragenter", highlight, false);
    dropArea.addEventListener("dragover", highlight, false);
    dropArea.addEventListener("dragleave", unhighlight, false);
    dropArea.addEventListener("drop", handleDrop, false);

    return {
        handleFiles
    };
}
const dropFile = new DropFile("drop-file", "files");
/* 파일 업로드 끝 */

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