let data = null;
let selectedSpeakers = [];

// FOMC Speech 크롤링하는 함수
async function getFOMCSpeeches() {
    try {
        const response = await fetch("/frSocialData", {
            method: "GET"
        });
        data = await response.json();
        if (response.ok) {
            console.log("Received Speech Data:", data);
            displayData(data);
        } else {
            console.error("Error from server:", data);
            return null; 
        }
    } catch (error) {
        console.error("Fetch Error:", error);
        return null; 
    }
}

//최근 10개를 화면에 뿌려주는 함수
async function displayData(datas) {
    const fomcSpeechList = document.querySelector('.fomc-speach-list');
    fomcSpeechList.innerHTML = '';
    //10개 이하면 다 보여주고, 10개 넘어가면 최근 10개만 잘라서 보여준다
    if (datas.data.length < 10) {
        for (let i = 0; i < datas.data.length; i++) {
            const item = datas.data[i]
            const div = document.createElement('div');
            div.className = 'fomc-speach-list';
            div.innerHTML = `
                <div class="box-flex-wrap">
                    <span class="date-label">${item.date}</span>
                    <div class="left-img-wrap">
                        <img src="/static/assets/images/${decodeURIComponent(item.author.split(" ").pop().toLowerCase())}.png" alt="" />
                </div>
                <div class="box-content">
                    <h4 class="box-content-tit">${item.title}</h4>
                    <p class="box-content-stit">${item.author}</p>
                    <div class="box-content-btn-wrap">
                        <a href="${item.link}" class="box-content-btn green" target="_blank">원문보기</a>
                        <button class="box-content-btn orange ai-summary-pop">AI 요약하기</button>
                    </div>
                </div>
            </div>
            `;
            fomcSpeechList.appendChild(div);
        }
    }
    else {
        for (let i = 0; i < 10; i++) {
            const item = datas.data[i]
            const div = document.createElement('div');
            div.className = 'fomc-speach-list';
            div.innerHTML = `
                <div class="box-flex-wrap">
                    <span class="date-label">${item.date}</span>
                    <div class="left-img-wrap">
                        <img src="/static/assets/images/${decodeURIComponent(item.author.split(" ").pop().toLowerCase())}.png" alt="" />
                </div>
                <div class="box-content">
                    <h4 class="box-content-tit">${item.title}</h4>
                    <p class="box-content-stit">${item.author}</p>
                    <div class="box-content-btn-wrap">
                        <a href="${item.link}" class="box-content-btn green" target="_blank">원문보기</a>
                        <button class="box-content-btn orange ai-summary-pop" onClick='dialogPop(this)';>AI 요약하기</button>
                    </div>
                </div>
            </div>
            `;
            fomcSpeechList.appendChild(div);
    }}
}

// 요약하기 버튼 눌렀을 때 팝업 띄우고 내용 보여주는 함수
function dialogPop(button){
    
    // Find the closest parent .box-flex-wrap element of the clicked button
    var boxWrapElement = button.closest('.box-flex-wrap');

    // Check if boxWrapElement is found
    if (boxWrapElement) {
        // Get the speech title and link within the boxWrapElement
        var speechTitle = boxWrapElement.querySelector('.box-content-tit').textContent;
        var speechLink = boxWrapElement.querySelector('.box-content-btn.green').getAttribute('href');

        // Now you have the speech title and link, you can use them as needed
        console.log("Speech Title:", speechTitle);
        console.log("Speech Link:", speechLink);
        document.body.style.pointerEvents = 'none'; //이거 하는 동안 다른 동작 금지
        document.getElementById('loading_bar_fomc').style.display = 'block';
        // Make a POST request to API endpoint with the speech information   
        fetch('/summarizeSpeech', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ title: speechTitle, link: speechLink }),
        })
        .then(response => response.json())
        .then(data => {
            document.body.style.pointerEvents = 'auto'; //다시 활성화
            // console.log(data.summary);
            document.getElementById('loading_bar_fomc').style.display = 'none';
            const summaryContent = document.getElementById("aiSummary");

            // pop-tit 요소에 내용을 넣어줍니다.
            let popTitElement = document.querySelector('#aiSummary .pop-tit');
            popTitElement.innerText = data.title;

            // pop-cont-wrap 요소에 내용을 넣어줍니다.
            let popContWrapElement = document.querySelector('#aiSummary .pop-cont-wrap');
            popContWrapElement.innerText = data.summary;

            $('#aiSummary').dialog({
            dialogClass : 'research-dialog',
            title : '',
            modal : true,
            draggable : false,
            resizable : false,
            autoOpen: false,
            width: 700,
            height: 500,
            open : function(){
                $('.ui-widget-overlay').on('click', function(){     
                $('#aiSummary').dialog('close');
            });
            }
            });    
            $('#aiSummary').dialog('open');
            })

        .catch(error => {
            document.body.style.pointerEvents = 'auto'; //다시 활성화
            document.getElementById('loading_bar_fomc').style.display = 'none';
            console.error('Error:', error)
        });
        
    } else {
        console.error("Parent .box-flex-wrap element not found.");
    }
    

}

// async function loadMoreData() {
//     // 버튼 눌렀을 때 나머지 내용 다 떨굼
//     console.log("Clicked!");
//     console.log(data);
//     const morefomcSpeechList = document.querySelector('.view-more');
//     morefomcSpeechList.innerHTML = '';//let i = 0; i < 5; i++  const item of data.data
//     for (let i = 7; i < data.data.length; i++) {
//         const item = data.data[i]
//         const div = document.createElement('div');
//         div.className = 'fomc-speach-list';
//         div.innerHTML = `
//             <div class="box-flex-wrap">
//                 <span class="date-label">${item.date}</span>
//                 <div class="left-img-wrap">
//                     <img src="/static/assets/images/${decodeURIComponent(item.author.split(" ").pop().toLowerCase())}.png" alt="" />
//             </div>
//             <div class="box-content">
//                 <h4 class="box-content-tit">${item.title}</h4>
//                 <p class="box-content-stit">${item.author}</p>
//                 <div class="box-content-btn-wrap">
//                     <a href="${item.link}" class="box-content-btn green" target="_blank">원문보기</a>
//                     <button class="box-content-btn orange ai-summary-pop">AI 요약하기</button>
//                 </div>
//             </div>
//         </div>
//         `;
//         morefomcSpeechList.appendChild(div);
//     }
// }

// 모든 체크박스 요소를 가져와서 각각에 대해 이벤트 리스너 추가

function getCheckboxValue(event)  {
    let result = '';

    //체크 되었을 때 또는 체크 해지되었을때 해당 연설자 이름 가져오기
    if(event.target.checked)  {
      result = event.target.value;
    }else {
      result = event.target.value;
    }
    
    let index = selectedSpeakers.indexOf(result);
    // console.log(index);

    // item 요소가 배열에 있는 경우
    if (index !== -1) {
    // 배열에서 item 요소를 제거
    selectedSpeakers.splice(index, 1);
    } else {
    // 배열에 item 요소가 없는 경우, 배열에 item 요소 추가
    selectedSpeakers.push(result);
    }
    // console.log(selectedSpeakers);
  }

function clearCheckboxes(event) {
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');    
    // 모든 체크박스 선택 해제
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    selectedSpeakers = []
    console.log(`Array Cleared: now ${selectedSpeakers.length} selected`);
    getFOMCSpeeches();
}

// 체크한 연설자 기준으로 연설문 필터링
function filterSpeeches(event) {
    if (selectedSpeakers.length === 0) {
        alert("최소 한 명이라도 선택해주세요.");
    }
    else {
        const lastNames = selectedSpeakers.map(speaker => {
        return speaker.split(" ").pop();
    }); // Governor Cook -> Cook만 저장
    console.log(lastNames);
    let filtered_list = [];
    // console.log(data);
    // data.data 배열을 순회하면서 speaker list에 있는 저자인지 확인
    data.data.forEach(item => {
        // console.log(item);
        const lastName = decodeURIComponent(item.author.split(" ").pop());
        // console.log(lastNames)
        if (lastNames.includes(lastName)) {
            filtered_list.push(item);
        }
    });
    //필터링된 데이터를 다시 JSON 화 시킨다
    const filtered = JSON.parse(JSON.stringify({"data": filtered_list}));
    //화면에 뿌려주기
    displayData(filtered);

}}



