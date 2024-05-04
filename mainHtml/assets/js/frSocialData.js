let data = null;
let selectedSpeakers = [];
let articleData = null;
// FOMC 페이지 내에서 Menu탭 이동
function fomcMenuChange(type){
    let htmlPath = '';
    if(type === 'press'){
        htmlPath = 'frSocialPress.html';
        fomcScrapingAPI('/fomc-scraping-release/?url=https://www.federalreserve.gov/json/ne-press.json');        
    }else if(type === 'summary'){
        htmlPath = 'frSocialData.html';
        getFOMCSpeeches();
    }else{
        htmlPath = 'frSocialAnalysis.html';
        //getArticleData();
    }
    $('#right-area').load(htmlPath); // HTML 파일의 내용을 로드하여 right-area에 삽입
}

/********************************** [프레스 릴리스 ] ******************************************/
// FOMC 사이트가서 데이터 긁어온다 
async function fomcScrapingAPI(url) {
    try {
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            displayFomcData(data);
        } else {
            console.error('Failed to fetch fomc main data:', response.status);
        }
    } catch (error) {
        console.error('An error occurred:', error);
    }
} 

// FOMC 메인 타이틀 뉴스들 보여주기
function displayFomcData(data) {
    console.log(data);
    const container = document.getElementById('fomc_press_releases');
    container.innerHTML = ''; 
    data.forEach(item => {
        const div = document.createElement('div');
        // Updated class name to match new naming convention
        div.className = 'fomc-release-item'; 
        div.innerHTML = `
            <h3 data-link="${item.link}">${item.title}</h3>
            <div class="dis-flex">
                <p>Date: ${item.datetime}</p>
                <p>Press Type: ${item.press_type}</p>
            </div>
            <button class="fomc-release-summary-btn" onclick="fetchFomcReleaseDetail('${item.link}', this.parentElement.querySelector('.fomc-release-detail'))">Press Release AI 요약내용 보기</button>
            <div class="fomc-release-detail"></div>
        `;
        container.appendChild(div);
        document.getElementById('fomc_press_releases').style.display = 'block';   
    });
}

// FOMC 상세 데이터 다시 스크래핑
async function fetchFomcReleaseDetail(link, detailContainer) {
    const detailButton = detailContainer.previousElementSibling;
    
    // 토글 기능을 추가
    if (detailContainer.classList.contains('fomc-detail-shownNews')) {
        detailContainer.classList.remove('fomc-detail-shownNews');
        detailContainer.classList.add('fomc-detail-hiddenNews');
        detailContainer.style.display = 'none'; 
        detailButton.textContent = 'Press Release AI 요약내용 보기';
        return;
    } else {
        try {
            const filename = link.split('/').pop().split('.')[0]; 
            const filePath = `/batch/fomc/fomc_detail_${filename}.txt`;
            const fileResponse = await fetch(filePath);
            let detailData;        
            if (fileResponse.ok) {
                detailData = await fileResponse.text();
            } else {
                var loadingText = document.getElementById('loading-text-fomc-press');
                loadingText.textContent = 'Press Release 내용분석중입니다. 조금만 기다려주세요.';
                document.getElementById('loading_bar_fomc_press').style.display = 'block';
                    
                const response = await fetch(`/fomc-scraping-details-release?url=${encodeURIComponent(link)}`);
                if (!response.ok) {
                    console.error('Failed to fetch detail:', response.status);
                    detailContainer.innerHTML = '<p>Error loading details.</p>';
                    return;
                }     
                detailData = await response.text();
            }        
            detailData = detailData.replace(/\*\*(.*?)\*\*/g, '<span class="highlight_news">$1</span>');
            detailData = detailData.replace(/\\n/g, '\n').replace(/\n/g, '<br>');
            let detailDiv = document.createElement('div');
            detailDiv.className = 'fomc-detail-content';
            detailDiv.innerHTML = detailData;
            
            detailContainer.innerHTML = '';
            detailContainer.appendChild(detailDiv);
            setTimeout(() => {
                detailContainer.classList.remove('fomc-detail-hiddenNews');
                detailContainer.classList.add('fomc-detail-shownNews');
                detailContainer.style.display = 'block'; 
                const totalHeight = detailContainer.scrollHeight;
                detailContainer.style.maxHeight = `${totalHeight}px`;
                detailButton.textContent = 'Press Release AI 요약 닫기';
            }, 2);                  
        } catch (error) {
            console.error('An error occurred:', error);
            detailContainer.innerHTML = '<p>Error loading details.</p>';
        } finally {
            var loadingText = document.getElementById('loading-text-fomc-press');
            loadingText.textContent = '데이터 로딩중입니다.';
            document.getElementById('loading_bar_fomc_press').style.display = 'none';
        }
    }
}


/*********************************  [ 요약 ] **************************************************/
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
    var boxWrapElement = button.closest('.box-flex-wrap');

    if (boxWrapElement) {
        var speechTitle = boxWrapElement.querySelector('.box-content-tit').textContent;
        var speechLink = boxWrapElement.querySelector('.box-content-btn.green').getAttribute('href');

        var filename = speechLink.split('/').pop().split('.')[0];  
        var filePath = `/batch/fomc/fomc_speech_ai_sum_${filename}.json`;  

        document.body.style.pointerEvents = 'none'; // Disable other interactions
        document.getElementById('loading_bar_fomc').style.display = 'block';

        // 파일 저장된것 있는지 먼저 체크
        fetch(filePath)
        .then(response => {
            if (!response.ok) throw new Error('Not found');  
            return response.json();
        })
        .then(data => {
            updateUI(data);  // 화면 그려주기 함수 따로 뺌
        })
        .catch(error => {
            // 파일 없을때만 서버호출
            fetch('/summarizeSpeech', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title: speechTitle, link: speechLink })
            })
            .then(response => response.json())
            .then(data => {
                updateUI(data);  
            })
            .catch(error => {
                console.error('Error:', error);
                document.body.style.pointerEvents = 'auto';
                document.getElementById('loading_bar_fomc').style.display = 'none';
            });
        });
    } else {
        console.error("Parent .box-flex-wrap element not found.");
    }
}

function updateUI(data) {
    document.body.style.pointerEvents = 'auto';
    document.getElementById('loading_bar_fomc').style.display = 'none';

    let popTitElement = document.querySelector('#aiSummary .pop-tit');
    popTitElement.innerText = data.title;

    let popContWrapElement = document.querySelector('#aiSummary .pop-cont-wrap');
    popContWrapElement.innerText = data.summary;

    $('#aiSummary').dialog({
        dialogClass: 'research-dialog',
        title: '',
        modal: true,
        draggable: false,
        resizable: false,
        autoOpen: false,
        width: 700,
        height: 500,
        open: function() {
            $('.ui-widget-overlay').on('click', function(){
                $('#aiSummary').dialog('close');
            });
        }
    });
    $('#aiSummary').dialog('open');
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

/*****************************  [ 성향분석 ] *********************************************/

// Radio Box 에 있는 value를 읽어 그 사람에 해당하는 스피치나 기사를 가져온다.
// 스피치나 기사를 가져온 후 LLM에게 던진다
// 스피치 --> 주요문장 추출 --> 감성분석 결과와 주요문장
// 기사 --> 그냥 제목을 보내서 --> 감성분석 결과와 타이틀

function getSelectedRadioValue() {
    var radioButtons = document.getElementsByName('radio');

    for (var i = 0; i < radioButtons.length; i++) {
        if (radioButtons[i].checked) {
            return radioButtons[i].value;
        }
    }

    // 만약 선택된 라디오 버튼이 없을 경우에 대한 처리
    return null;
}

// 타임라인 그래프 그려주는 함수
// chartData가 실제데이터고 isSpeech는 스피치데이터인지 기사데이터인지 가리는 boolean값임
function plotTimeline(chartData, isSpeech) {
    // 스피치냐 기사냐에 따라 제목 바꿔주기
    let titleText;
    if (isSpeech) {
        titleText = 'Speech';
    } else {
        titleText = 'Article';
    }

    // Highcharts 그래프 생성
    Highcharts.chart('timelineContainer', {
        chart: {
            zoomType: 'x',
            type: 'timeline'
        },
        xAxis: {
            type: 'datetime',
            visible: false
        },
        yAxis: {
            gridLineWidth: 1,
            title: null,
            labels: {
                enabled: false
            }
        },
        title: {
            text: `${titleText} Timeline`
        },
        tooltip: {
            style: {
                width: 300
            }
        },
        series: [{
            dataLabels: {
                allowOverlap: false,
                // format: '<span style="color:{point.color}">● </span><span style="font-weight: bold;" > ' +
                //     '{point.x:%d %b %Y}</span><br/>{point.label}',
                formatter: function() {
                    return '<span style="color:' + this.point.color + '">● </span><span style="font-weight: bold;" > ' +
                    Highcharts.dateFormat('%e %b %Y', this.x) + '</span><br/>' + this.point.label;
                }
            },

            marker: {
                symbol: 'circle'
            },
            data: chartData
        }]
    });
}


//감성분석 점수 보여주는 함수
function plotScore(data) {
    data = data.reverse() //오래전이 제일 먼저 오게 하기

    // 차트 그리기
    Highcharts.chart('scoreContainer', {
        chart: {
            type: 'column'
        },
        title: {
            text: 'Dovish-Hawkish Score Timeline'
        },
        xAxis: {
            categories: data.map(item => item.date)
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Scores'
            }
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> ({point.percentage:.0f}%)<br/>',
            shared: true
        },
        plotOptions: {
            column: {
                stacking: 'percent',
                dataLabels: {
                    enabled: true,
                    format: '{point.percentage:.0f}%'
                }
            }
        },
        series: [{
            name: 'Neutral',
            color: '#F5DF4D',
            data: data.map(item => {
                var neutralScore = item.scores[0].find(score => score.label === "LABEL_2").score;
                return neutralScore * 100; // converting to percentage
            })
        }, {
            name: 'Dovish',
            color: '#93A9D1',
            data: data.map(item => {
                var dovishScore = item.scores[0].find(score => score.label === "LABEL_0").score;
                return dovishScore * 100; // converting to percentage
            })
        }, {
            name: 'Hawkish',
            color: '#FF6F61',
            data: data.map(item => {
                var hawkishScore = item.scores[0].find(score => score.label === "LABEL_1").score;
                return hawkishScore * 100; // converting to percentage
            })
        }]
    });
}


function generateScore(data, isSpeech) {
    // post 요청으로 데이터에 대한 성향분석 점수를 받아옴
    // {date: "2020/04/04", scores: [], result: " "} 이런식으로 결과가 와야됨
    // api 호출해서 점수 받아오기
    fetch('/sentimentScore', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({speeches: data, is_speech: isSpeech})
            //n_graphs: parseInt(nGraphs, 10)
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        plotScore(data);
    
    })
    .catch(error => {
        console.error('Error fetching sentiment score:', error);
        // document.getElementById('loading_bar_similarity').style.display = 'none'; 
    });

}

function generateTimeline() {
    var selectedValue = getSelectedRadioValue();
    if (selectedValue) {
        // 선택된 값이 있다면 여기에 원하는 동작을 수행할 수 있습니다.
        console.log("선택된 라디오 버튼의 값:", selectedValue);
    
        const boardMembers = ['Jerome Powell', 'Philip Jefferson', 'Michael Barr',
         'Michelle Bowman', 'Lisa Cook', 'Adriana Kugler', 'Christopher Waller'];
        // 7명의 사람들에 해당될 경우 스피치
        if (boardMembers.includes(selectedValue)) {
            const lastName = selectedValue.split(" ").pop(); //Jerome Powell => Powell만 저장

            let filtered_list = [];
            // console.log(data);
            // data.data 배열을 순회하면서 speaker list에 있는 저자인지 확인
            data.data.forEach(item => {
                // console.log(item);
                const itemLastName = decodeURIComponent(item.author.split(" ").pop());
                // console.log(lastNames)
                if (lastName === itemLastName) {
                    filtered_list.push(item);
                }  
            });

            fetch('/sentimentAnalysis', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({speeches: filtered_list})
                    //n_graphs: parseInt(nGraphs, 10)
            })
            .then(response => response.json())
            .then(data => {
                console.log(data);
                var chartData = data.map(function(item) {
                    // const parts = item.date.split('/');
                    // const jsDate = new Date(parts[2], parts[0] - 1, parts[1]);
                    return {
                        x: new Date(item.date),
                        name: item.title,
                        label: item.title,
                        description: item.result
                    };
                });
                plotTimeline(chartData, true);
                generateScore(data, true);
            })
            .catch(error => {
                console.error('Error fetching similarity data:', error);
                // document.getElementById('loading_bar_similarity').style.display = 'none'; 
            });
            
        }       
        else {
            //5명의 사람들에 해당될 경우 기사
            //selectedValue = John Williams, Thomas Barkin, Raphael Bostic, Mary Daly, Loretta Mester
            fetch('/articleData', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({name: selectedValue})
            })
            .then(response => response.json())
            .then(data => {
                console.log(data);
                // regex를 사용해서 link 끝에 있는 날짜 섹션 (ex. 2024-04-04)을 추출해서 date로 바꾼다
                data.forEach(item => {
                    // console.log(item);
                    const regex = /(\d{4}-\d{2}-\d{2})/;
                    const match = item.link.match(regex);
    
                    // 매칭된 부분을 출력
                    const date = match ? match[0] : null;
                    // console.log(date);
                    item.date = date; //바꿔버려
                });
                //데이터를 날짜순으로 정렬
                data.sort((a, b) => new Date(b.date) - new Date(a.date));
                // console.log(data);
                var chartData = data.map(function(item) {
                    // const parts = item.date.split('/');
                    // const jsDate = new Date(parts[2], parts[0] - 1, parts[1]);
                    return {
                        x: new Date(item.date),
                        name: item.title,
                        label: item.title,
                        description: item.snippet
                    };
                });
               
                plotTimeline(chartData, false);
                generateScore(data, false);
            })
            .catch(error => {
                console.error('Error fetching similarity data:', error);
                // document.getElementById('loading_bar_similarity').style.display = 'none'; 
            });

        }

    } else {
        // 선택된 값이 없을 경우에 대한 처리
        console.log("라디오 버튼이 선택되지 않았습니다.");
        alert("성향 분석 변화 추이를 보고 싶은 연사를 선택해주세요.");
    }
}



