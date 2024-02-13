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
                    // 버튼 생성 및 설정
                    var ocrButton = document.createElement("button");
                    ocrButton.textContent = "OCR Data Read";
                    ocrButton.className = "ocrButton"; // 여기에서 클래스 이름을 지정
                    ocrButton.onclick = function() {
                        // OCR 처리 함수 호출
                        performOCR(canvas);
                    };
                    // 'ocrArea' 내에 버튼 추가
                    document.getElementById('ocrArea').appendChild(ocrButton);
                });
            });
        });
    };
    fileReader.readAsArrayBuffer(file);
    document.getElementById('fileName').textContent = file.name;
});


