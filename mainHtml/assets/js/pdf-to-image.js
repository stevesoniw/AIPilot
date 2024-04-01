document.getElementById('fileInput').addEventListener('change', function(event) {
    var file = event.target.files[0];
    if (file.type !== 'application/pdf') {
        console.error(file.name, 'is not a PDF file.');
        return;
    }

    var fileReader = new FileReader();
    fileReader.onload = function() {
        var typedarray = new Uint8Array(this.result);

        // PDF.js를 사용하여 PDF 문서 로드
        pdfjsLib.getDocument(typedarray).promise.then(function(pdf) {
            console.log(`PDF loaded with ${pdf.numPages} pages.`);

            // 첫 번째 페이지 로드
            pdf.getPage(1).then(function(page) {
                var canvas = document.getElementById('pdfCanvas');
                var context = canvas.getContext('2d');
                canvas.hidden = false;

                // 뷰포트 설정
                var viewport = page.getViewport({scale: 1.5});
                canvas.height = viewport.height;
                canvas.width = viewport.width;

                // 페이지 렌더링
                var renderContext = {
                    canvasContext: context,
                    viewport: viewport
                };
                page.render(renderContext).promise.then(function() {
                    console.log('Page rendered');
                    // 버튼 공통 설정 함수
                    function createButton(id, text, onClickFunction) {
                        var button = document.createElement("button");
                        button.id = id;
                        button.textContent = text;
                        button.className = "ocrButton"; // 모든 버튼에 같은 클래스 적용
                        button.onclick = onClickFunction;
                        return button;
                    }

                    // OCR Data Read 버튼
                    var ocrButton = createButton("ocrButton", "OCR Data Read", function() { performOCR(canvas); });

                    // OCR GPT 버튼
                    var ocrGptButton = createButton("ocrGptButton", "OCR GPT Read", function() { ocrGptTest(canvas); });

                    // Interest Data 버튼
                    var interestButton = createButton("interestButton", "Interest Data", function() { interestData(canvas); });

                    // buttonsContainer 내에 버튼 추가
                    var container = document.getElementById('buttonsContainer');
                    container.appendChild(ocrButton);
                    container.appendChild(ocrGptButton);
                    container.appendChild(interestButton);
                });
            });
        });
    };
    fileReader.readAsArrayBuffer(file);
    document.getElementById('fileName').textContent = file.name;
});


