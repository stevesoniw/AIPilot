
//*********************************** AI가 말해주는 주식정보 함수 Starts [#1.Get EarningIfno]********************************************//
// 버튼 on, off 컨트롤
function addButtonOn(buttonId) {
    const button = document.getElementById(buttonId);
    if (!button.classList.contains('on')) {
        button.classList.add('on');
    }
}

function removeButtonOn(buttonId) {
    const button = document.getElementById(buttonId);
    if (button.classList.contains('on')) {
        button.classList.remove('on');
    }
}

//FinGPT 최근 실적발표 History 및 애널리스트 추천 트렌드 차트보여주기
async function loadEarningData() {
    addButtonOn('getEarningInfo');
    removeButtonOn('getStockInfo');
    removeButtonOn('getForeignStockNews'); 
    const ticker = document.getElementById('foreign_ticker').value;             
    try {
        //로딩바
        document.getElementById('loading_bar_fingpt').style.top = '30%';  
        document.getElementById('loading_bar_fingpt').style.display = 'block';                    
        //뉴스
        document.getElementById('loading_bar_foreignnews').style.display = 'none';
        document.getElementById('foreignTickerNewsArea').style.display = 'none';
        document.getElementById('fomc-press-releases').style.display = 'none';
        //기본정보
        document.getElementById('loading_bar_stockbasic').style.display = 'none';
        document.getElementById('stockBasic').style.display = 'none';
        //챗
        document.getElementById('chatApp').style.dispaly = 'none';

        if (!ticker) {
            alert('종목을 먼저 선택해주세요!');
            document.getElementById('loading_bar_fingpt').style.display = 'none';  
            return;
        }

        const todayDate = new Date().toISOString().slice(0, 10).replace(/-/g, "");
        const fileUrl = `/batch/earning_data/${ticker}/earningChart_${ticker}_${todayDate}.json`;
        let data;

        try {
            // 먼저 파일에서 데이터를 읽어보기
            const fileResponse = await fetch(fileUrl);
            if (!fileResponse.ok) throw new Error('File not found, fetching from server...');
            data = await fileResponse.json();
        } catch (error) {
            // 파일이 없으면 서버에서 데이터 가져오기
            const response = await fetch(`/api/charts/both/${ticker}`);
            data = await response.json();
        }
        // Base64 인코딩된 이미지 데이터를 이미지 태그의 src 속성에 할당
        document.getElementById('earningsChart').src = 'data:image/png;base64,' + data.earnings_chart;
        document.getElementById('recommendationsChart').src = 'data:image/png;base64,' + data.recommendations_chart;

        // 차트 영역을 보이게 설정
        document.getElementById('fingptChartArea').style.display = 'block';
        document.getElementById('loading_bar_fingpt').style.display = 'none';  
        //fetchEarningsAnnouncement(ticker);
        gptAnalysis(ticker);

    } catch (error) {
        console.error('Error loading chart data:', error);
        //fetchEarningsAnnouncement(ticker);
        gptAnalysis(ticker);
        document.getElementById('fingptChartArea').style.display = 'none';
        document.getElementById('loading_bar_fingpt').style.display = 'none'; 
    }
}

function releaseButtonState() {
    const button = document.getElementById('getEarningInfo');
    button.classList.remove('on'); // 'on' 클래스 제거
}

//실적발표 테이블 표 만들어서 보여주기
async function fetchEarningsAnnouncement(ticker) {
    const apiUrl = `/foreignStock/financials/earningTable/${ticker}`;
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error('서버에서 데이터를 가져오는 데 실패했습니다. 응답 상태: ' + response.status);
        }
        const data = await response.json();
        if (data) {
            document.getElementById('gptEarningTableArea').style.display = 'block';
            document.getElementById('latest_quarter_revenue').textContent = data.latest_quarter_revenue ? data.latest_quarter_revenue.toLocaleString() + ' (USD)' : '-';
            document.getElementById('revenue_yoy_percentage').textContent = typeof data.revenue_yoy_percentage === 'number' ? data.revenue_yoy_percentage.toFixed(2) + '%' : '-';
            document.getElementById('revenue_qoq_percentage').textContent = typeof data.revenue_qoq_percentage === 'number' ? data.revenue_qoq_percentage.toFixed(2) + '%' : '-';
            document.getElementById('revenue_beat_miss_ratio').textContent = typeof data.revenue_beat_miss_ratio === 'number' ? data.revenue_beat_miss_ratio.toFixed(2) + '%' : '-';
            document.getElementById('latest_quarter_operating_income').textContent = typeof data.latest_quarter_operating_income ? data.latest_quarter_operating_income.toLocaleString() + ' (USD)': '-';
            document.getElementById('operating_income_yoy_percentage').textContent = typeof data.operating_income_yoy_percentage === 'number' ? data.operating_income_yoy_percentage.toFixed(2) + '%' : '-';
            document.getElementById('operating_income_qoq_percentage').textContent = typeof data.operating_income_qoq_percentage === 'number' ? data.operating_income_qoq_percentage.toFixed(2) + '%' : '-';
            document.getElementById('eps_beat_miss_ratio').textContent = typeof data.eps_beat_miss_ratio === 'number' ? data.eps_beat_miss_ratio.toFixed(2) + '%' : '-';
        }
        gptAnalysis(ticker);
    } catch (error) {
        document.getElementById('gptEarningTableArea').style.display = 'none';
        gptAnalysis(ticker);
        console.error('Error Fetching 실적발표 테이블:', error.message);
    }
}

//FinGPT 실적발표 전후 반응 + 근거 문서 갖고와서 보여주기 
async function gptAnalysis(ticker) {
    try {   
        //데이터 일단 클리어
        document.getElementById('analysisResult').innerHTML = "";    
        document.getElementById('newsAnalysis').innerHTML = "";                     
        document.getElementById('gptMessageArea').style.display = 'block';
        document.getElementById('loading_bar_fingpt').style.top = '80%';  
        document.getElementById('loading_bar_fingpt').style.display = 'block';  

        const todayDate = new Date().toISOString().slice(0, 10).replace(/-/g, "");
        const fileUrl = `/batch/earning_data/${ticker}/gptAnalysis_${ticker}_${todayDate}.json`;        
        const checkResponse = await fetch(fileUrl);
        let data;
        //File 이 있으면 File에서 먼저 읽는다. for 속도개선. 
        if (checkResponse.ok) {
            data = await checkResponse.json();
        } else {
            const response = await fetch(`/api/analysis/${ticker}`);
            data = await response.json();
        }     
        if(data){
            const formattedCompletion = data.completion.replace(/\n/g, '<br>');
            const formattedPrompt = data.prompt_news.replace(/\n/g, '<br>');
            document.getElementById('analysisResult').innerHTML = formattedCompletion;
            document.getElementById('newsAnalysis').innerHTML = formattedPrompt;
            document.getElementById('loading_bar_fingpt').style.display = 'none';   
            gptStockWave(ticker)                      
        }

    }catch (error) {
        console.error('Error loading Stock Analysis:', error);
        document.getElementById('gptMessageArea').style.display = 'none';
        document.getElementById('loading_bar_fingpt').style.display = 'none'; 
    }                
}
//FinGPT 최근 1년 주가 흐름과 거래량 추이 보여주기 (이미지 호출->하이차트로 변경 2024.04.10)

async function gptStockWave(ticker) {
    try {
        document.getElementById('loading_bar_fingpt').style.display = 'block';  
        document.getElementById('gptStockwaveArea').style.display = 'none';

        const response = await fetch(`/api/stockwave/${ticker}`);
        const data = await response.json();

        // 현재 날짜와 1년 전 날짜 계산
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
        const minDate = oneYearAgo.getTime();

        // 최신 날짜(데이터의 마지막 날짜) 계산
        const maxDate = new Date(data.dates[data.dates.length - 1]).getTime();

        var selectedData = $('#foreign_ticker').select2('data');
        if (selectedData.length > 0) {
            var description = selectedData[0].text; 
        }

        Highcharts.stockChart('gptStockwaveArea', {
            chart: {
                zoomType: 'xy'
            },
            rangeSelector: {
                selected: 5, // 'All' 범위 선택. 실제 범위는 xAxis의 min, max로 제어됩니다.
                inputEnabled: false,
            },
            navigator: {
                enabled: true
            },
            title: {
                //text: `${ticker} 1년 주가 데이터와 거래량`,
                text: `${description} 1년 주가 데이터와 거래량`,
                style: {
                    color: '#13064e', // 진남색
                    fontSize: '17px' // 글자 크기
                }
            },
            xAxis: {
                min: minDate,
                max: maxDate,
            },
            series: [{
                name: `${ticker} Price`,
                data: data.dates.map((date, index) => [new Date(date).getTime(), data.prices[index]]),
            }, {
                name: 'Volume',
                type: 'column',
                data: data.dates.map((date, index) => [new Date(date).getTime(), data.volumes[index]]),
                yAxis: 1,
            }],
            yAxis: [{
                title: {
                    text: 'Stock Price'
                },
                height: '60%',
                resize: {
                    enabled: true
                },
                labels: {
                    align: 'right',
                    x: -3
                }
            }, {
                title: {
                    text: 'Volume'
                },
                top: '65%',
                height: '35%',
                offset: 0,
                lineWidth: 2,
                opposite: true, // 거래량을 오른쪽에 배치
                labels: {
                    align: 'right',
                    x: -3
                }
            }],
            credits: {
                enabled: false
            }
        });

        document.getElementById('loading_bar_fingpt').style.display = 'none';  
        document.getElementById('gptStockwaveArea').style.display = 'block';
    } catch (error) {
        console.error('Error loading stockwave data:', error);
        document.getElementById('loading_bar_fingpt').style.display = 'none'; 
        document.getElementById('gptStockwaveArea').style.display = 'none';                
    }
}



//*********************************** AI가 말해주는 주식정보 함수 Ends [#1.Get EarningIfno]****************************************//        
//********************************** AI가 말해주는 주식정보 함수 Starts [#2.Get ForeignStockNewsInfo]**************************************//
//Finnhub에서 해외 종목 뉴스데이터 가져오기 
async function loadForeignStockNews() {
    addButtonOn('getForeignStockNews');
    removeButtonOn('getEarningInfo');
    removeButtonOn('getStockInfo');  
    //실적
    document.getElementById('loading_bar_fingpt').style.display = 'none';
    document.getElementById('fingptChartArea').style.display = 'none';
    document.getElementById('gptEarningTableArea').style.display = 'none';
    document.getElementById('gptMessageArea').style.display = 'none';
    document.getElementById('gptStockwaveArea').style.display = 'none';
    //뉴스
    //document.getElementById('loading_bar_foreignnews').style.display = 'none';
    //document.getElementById('foreignTickerNewsArea').style.display = 'none';
    //document.getElementById('fomc-press-releases').style.display = 'none';    
    //기본정보
    document.getElementById('loading_bar_stockbasic').style.display = 'none';
    document.getElementById('stockBasic').style.display = 'none';

    const ticker = document.getElementById('foreign_ticker').value;
    if (!ticker) {
        alert('종목을 먼저 선택해주세요!');
        document.getElementById('loading_bar_foreignnews').style.display = 'none';
        return;
    }
    document.getElementById('loading_bar_foreignnews').style.display = 'block';
    try {
        const response = await fetch(`/foreignStock/financials/news/${ticker}`);
        if (!response.ok) throw new Error('Failed to fetch foreign stock news info data');
        
        const data = await response.json();
        const newsContainer = document.getElementById('foreignTickerNewsArea');
        newsContainer.innerHTML = '';
        if (data.length === 0) {
            newsContainer.innerHTML = '<p style="padding-top:20px; color:orange; font-weight:bold;">최근 등록된 뉴스가 없습니다.</p>';
            return;
        }
        // 뉴스 항목 너무 많아서 최대 15개까지만 표시함
        data.slice(0, 15).forEach(news => {
            const newsDate = new Date(news.datetime * 1000).toISOString().slice(0, 10);
            const imageSrc = news.image || `/static/assets/images/defaultNews${Math.floor(Math.random() * 5) + 1}.jpg`;
            const newsElement = `
                    <div class="foreignTickerNews-container" data-news-id="${news.id}">
                    <span class="foreignTickerNews-datetime">${newsDate}</span>
                    <div class="foreignTickerNews-image">
                        <img src="${imageSrc}" alt="${news.related}">
                    </div>
                    <div class="foreignTickerNews-content">
                        <div class="foreignTickerNews-header">
                            <h2 class="foreignTickerNews-headline">${news.headline}</h2>
                            <span class="foreignTickerNews-source">${news.source}</span>
                        </div>
                        <p class="foreignTickerNews-summary">${news.summary}</p>
                        <div class="foreignTickerNews-buttons-container">
                            <a class="foreignTickerNews-link" href="${news.url}" target="_blank">read more</a>
                            <button class="foreignTickerNews-analysis" onclick="analyzeStockArticle('${news.url.replace(/'/g, "\\'")}', '${news.id}');">AI 기사분석</button>
                        </div>
                    </div>
                </div>
            `;
            newsContainer.insertAdjacentHTML('beforeend', newsElement);
            document.getElementById('foreignTickerNewsArea').style.display = 'block';
        });
    } catch (error) {
        console.error('Error fetching stock info:', error);
    } finally {
        document.getElementById('loading_bar_foreignnews').style.display = 'none';
        //FOMC 호출 연이어서..
        fomcScrapingAPI('/fomc-scraping-release/?url=https://www.federalreserve.gov/json/ne-press.json');
    }
}
function toggleVisibility(element) {
    if (element.classList.contains('hiddenNews')) {
        // 펼치기: 실제 필요한 최대 높이로 설정함
        element.classList.remove('hiddenNews');
        // scrollHeight를 사용하여 요소의 실제 높이를 계산하고, 여유분을 더하자
        element.style.maxHeight = element.scrollHeight + 'px';
    } else {
        // 접기ㅋ
        element.classList.add('hiddenNews');
        element.style.maxHeight = '0';
    }
}

function analyzeStockArticle(webUrl, newsId) {
    var loadingText = document.getElementById('loading-text-foreignnews');
    loadingText.textContent = '해당 뉴스의 원문사이트 분석중입니다. 뉴스출처에 따라 시간이 매우 오래걸릴수 있습니다. (*Finnhub뉴스는 차단당하는 경우가 존재하여 조치중입니다.)';
    document.getElementById('loading_bar_foreignnews').style.display = 'block';

    const ticker = document.getElementById('foreign_ticker').value;
    // 배치로 떨궈놓은 파일 있으면 일단 읽게한다. 
    var filename = `/batch/stocknews/${ticker}/${ticker}_${newsId}.txt`;
    fetch(filename)
    .then(response => {
        if (response.ok) {
            // 파일이 존재하는 경우 파일 데이터를 읽어옴
            console.log("file data exists!!!!")
            return response.text()
                .then(data => {
                    displayAnalysisResult(data, webUrl, newsId);
                });
        } else {
            return fetch('/rag/handle-analyze-webnews/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: webUrl })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`analyzeArticle not ok, status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.result) {
                    // 서버에서 받은 데이터를 화면에 표시
                    displayAnalysisResult(data.result.text, webUrl, newsId);
                }
            })
            .catch(error => {
                console.error("Error:", error.message);
            });
        }
    })
    .catch(error => {
        console.error("Error:", error.message);
    })
    .finally(() => {
        document.getElementById('loading_bar_foreignnews').style.display = 'none';
        loadingText.textContent = '데이터 로딩중입니다.';
    });

}

function displayAnalysisResult(data, webUrl, newsId) {
    const analysisContainer = document.createElement('div');
    analysisContainer.className = 'analysisResultContainer';
    let modifiedData = data.replace(/\n/g, '<br>');
    modifiedData = modifiedData.replace(/\*\*(.*?)\*\*/g, '<span class="highlight_news">$1</span>');
    analysisContainer.innerHTML = `
        <div class="analysisTitle">해당 원본뉴스 사이트(<span class="webUrl">${webUrl}</span>)를 분석한 내용입니다.</div>
        <div class="analysisContent">${modifiedData}</div>
    `;
    const newsElement = document.querySelector(`[data-news-id="${newsId}"]`);
    if (newsElement) {
        newsElement.insertAdjacentElement('afterend', analysisContainer);
    }
}
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
    const container = document.getElementById('fomc-press-releases');
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
        document.getElementById('fomc-press-releases').style.display = 'block';   
    });
}
//Fomc title 접기/펼치기 
function addGlobalToggle() {
    if (!document.getElementById('toggleFomcButton')) {
        const toggleButton = document.createElement('button');
        toggleButton.id = 'toggleFomcButton';
        toggleButton.className = 'fomc-toggle-visibility-btn';
        // 초기 상태 설정
        toggleButton.setAttribute('data-visible', 'true');
        toggleButton.innerText = 'FOMC PressRelease ON';
        
        toggleButton.onclick = function() {
            const isVisible = toggleButton.getAttribute('data-visible') === 'true';
            const releaseItems = document.querySelectorAll('#fomc-press-releases .fomc-release-item');
            releaseItems.forEach(toggleShowHide);
            
            // 토글 상태 업데이트 및 텍스트 변경
            if (isVisible) {
                toggleButton.innerText = 'FOMC PressRelease OFF'; 
                toggleButton.setAttribute('data-visible', 'false');
                toggleButton.style.color = 'white'; 
            } else {
                toggleButton.innerText = 'FOMC PressRelease ON'; 
                toggleButton.setAttribute('data-visible', 'true');
                toggleButton.style.color = '#fffb03';
            }
        };
        document.getElementById("fomc-press-releases").before(toggleButton);
    }
}
// FOMC 상세 내용 보이고 안보이고 컨트롤 
function toggleFomcDetailVisibility(detailContainer) {
    if (detailContainer.classList.contains('fomc-detail-hiddenNews')) {
        detailContainer.classList.remove('fomc-detail-hiddenNews');
        detailContainer.classList.add('fomc-detail-shownNews');
        detailContainer.style.display = 'block'; 
        detailContainer.style.maxHeight = detailContainer.scrollHeight + 'px';
        detailContainer.style.opacity = 1;
        detailContainer.style.padding = '20px';
    } else {
        detailContainer.classList.add('fomc-detail-hiddenNews');
        detailContainer.classList.remove('fomc-detail-shownNews');
        detailContainer.style.display = 'none'; 
        detailContainer.style.maxHeight = '0';
        detailContainer.style.opacity = 0;
        detailContainer.style.padding = '0 20px';
    }
}
function toggleShowHide(element) { //도저히 깨지는 이유를 모르겠어서 비슷한 기능함수 일단 다시만듬;
    // 'fade-in'이 적용되지 않은 초기 상태를 처리
    if (!element.classList.contains('fade-in') && !element.classList.contains('fade-out')) {
        element.classList.add('fade-out'); // 초기 상태에서 'fade-out'을 추가하여 첫 번째 토글에서 요소를 숨길 수 있도록 함
        setTimeout(() => { element.style.display = 'none'; }, 500);
    }
    else if (element.classList.contains('fade-out')) {
        element.classList.remove('fade-out');
        element.classList.add('fade-in');
        element.style.display = 'block';
    } else {
        element.classList.remove('fade-in');
        element.classList.add('fade-out');
        setTimeout(() => { element.style.display = 'none'; }, 500);
    }
}            
    // FOMC 상세 데이터 다시 스크래핑 
async function fetchFomcReleaseDetail(link, detailContainer) {
    try {
        var loadingText = document.getElementById('loading-text-foreignnews');
        loadingText.textContent = 'Press Release 내용분석중입니다. 조금만 기다려주세요.';
        document.getElementById('loading_bar_foreignnews').style.display = 'block';
        const response = await fetch(`/fomc-scraping-details-release?url=${encodeURIComponent(link)}`);
        if (response.ok) {
            let detailData = await response.text();
            // \n을 <br>로 변환
            detailData = detailData.replace(/\*\*(.*?)\*\*/g, '<span class="highlight_news">$1</span>');
            detailData = detailData.replace(/\\n/g, '\n').replace(/\n/g, '<br>');
            // 상세 데이터를 표시할 새로운 div 생성
            let detailDiv = document.createElement('div');
            detailDiv.className = 'fomc-detail-content';
            detailDiv.innerHTML = detailData;
            
            detailContainer.innerHTML = '';
            detailContainer.appendChild(detailDiv);
            //약간 텀 주자
            setTimeout(() => {
                detailContainer.classList.remove('fomc-detail-hiddenNews');
                detailContainer.classList.add('fomc-detail-shownNews');
                detailContainer.style.display = 'block'; 
                const totalHeight = detailContainer.scrollHeight;
                detailContainer.style.maxHeight = `${totalHeight}px`; // 도저히 안됨ㅠ지연 후 maxHeight 설정하자. 
            }, 2);                  
        } else {
            console.error('Failed to fetch detail:', response.status);
            detailContainer.innerHTML = '<p>Error loading details.</p>';
        }
    } catch (error) {
        console.error('An error occurred:', error);
        detailContainer.innerHTML = '<p>Error loading details.</p>';
    } finally {
        var loadingText = document.getElementById('loading-text-foreignnews');
        loadingText.textContent = '데이터 로딩중입니다.';
        document.getElementById('loading_bar_foreignnews').style.display = 'none';
    }
}

            
//********************************** AI가 말해주는 주식정보 함수 Ends [#2.Get ForeignStockNewsInfo]**************************************//        
//************************************** AI가 말해주는 주식정보 함수 Starts [#3.Get StockInfo]********************************************//
//디지털리서치 요청으로 종목코드 select 선택모듈로 변경
async function fetchForeignStockCodes() {
    try {
        const response = await fetch('/api/get_foreign_stock_symbols');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const selectElement = $('#foreign_ticker');
        const fragment = document.createDocumentFragment();

        data.forEach(stock => {
            let option = new Option(`${stock.description} (${stock.symbol})`, stock.symbol);
            fragment.appendChild(option);
        });

        selectElement.empty().append(fragment).select2({
            placeholder: "원하시는 종목을 검색해주세요!",
            allowClear: true,
            minimumResultsForSearch: 0 // 검색 활성화
        }).val(null).trigger("change");
    } catch (error) {
        console.error("Failed to fetch foreign stock codes: ", error);
    }
}
//해외 주식 기본 정보 및 차트 데이터 갖고와서 보여주기 (Get Stock Info)
async function loadBasicInfo() {
    addButtonOn('getStockInfo');
    removeButtonOn('getEarningInfo');
    removeButtonOn('getForeignStockNews');   
    //실적
    document.getElementById('loading_bar_fingpt').style.display = 'none';
    document.getElementById('fingptChartArea').style.display = 'none';
    document.getElementById('gptEarningTableArea').style.display = 'none';
    document.getElementById('gptMessageArea').style.display = 'none';
    document.getElementById('gptStockwaveArea').style.display = 'none';
    //뉴스
    document.getElementById('loading_bar_foreignnews').style.display = 'none';
    document.getElementById('foreignTickerNewsArea').style.display = 'none';
    document.getElementById('fomc-press-releases').style.display = 'none';
    //기본정보
    document.getElementById('stockBasic').style.display = 'flex';

    const ticker = document.getElementById('foreign_ticker').value;
    if (!ticker) {
        alert('종목을 먼저 선택해주세요!');
        document.getElementById('loading_bar_stockbasic').style.display = 'none';
        return;
    }
    document.getElementById('loading_bar_stockbasic').style.display = 'block';
    document.getElementById('chatApp').style.display = 'none';
    try {
        const response = await fetch(`/foreignStock/financials/${ticker}`);
        if (!response.ok) throw new Error('Failed to fetch foreign stock basic info data');

        const data = await response.json();
        displayFinancialData(data);
    } catch (error) {
        console.error('Error fetching stock info:', error);
    } finally {
        document.getElementById('loading_bar_stockbasic').style.display = 'none';
    }
}

function toggleStockBasicVisibility(element) {
    if (element.style.maxHeight !== '0px' && element.style.maxHeight !== '') {
        element.style.maxHeight = '0';
        element.setAttribute('data-visible', 'false');
    } else {
        element.style.maxHeight = element.scrollHeight + 'px';
        element.setAttribute('data-visible', 'true');
    }
}

//차트데이터 전처리 함수
function preprocessChartData(chartData) {
    // Timestamp 객체를 ISO 날짜 문자열로 변환
    chartData.annual_financials.years = chartData.annual_financials.years.map(date => 
        new Date(date).toISOString().split('T')[0]
    );

    chartData.quarterly_growth.quarters = chartData.quarterly_growth.quarters.map(date => 
        new Date(date).toISOString().split('T')[0]
    );

    // NaN 값을 처리 (예: NaN을 0으로 변환하거나, 또는 NaN 값을 포함하는 데이터 포인트를 제거)
    chartData.quarterly_growth.revenue_growth = chartData.quarterly_growth.revenue_growth.map(value => 
        isNaN(value) ? 0 : value
    );

    return chartData;
}
// 숫자를 억 단위로 변환하는 함수 (깔끔하게 보여주게)
function convertToBillion(value) {
    return (value / 100000000).toFixed(2) + '억';
}
// 특정 key들에 대한 단위를 추가하는 함수 (종목 기본정보 보여줄때 깔끔하게 보여지게)
function appendUnit(key, value) {
    if (value === null) {
        return "-";
    }
    const keysWithUSD = ['50일 평균가', '52주 신고가', '52주 신저가', '총 자산', '자기자본', '시가총액', '총 부채', '영업현금흐름'];
    const keysInBillion = ['총 자산', '자기자본', '시가총액', '총 부채', '영업현금흐름'];
    if (keysWithUSD.includes(key)) {
        if (keysInBillion.includes(key)) {
            return convertToBillion(value) + ' (USD)';
        }
        return value + ' (USD)';
    } else if (key === '발행주식 수') {
        return value + ' 주';
    } else if (key === 'PER' || key === 'PBR') {
        return Math.round(value * 100) / 100; // 소수점 셋째 자리에서 반올림
    }
    return value;
}
//종목 기본정보 실제적으로 display 해주는 함수 (Get Stock Info)
function displayFinancialData(data) {
    const stockBasicContainer = document.getElementById('stockBasic');
    stockBasicContainer.style.maxHeight = '0'; // 초기에 컨테이너를 접기용

    // 기업 및 추가 정보 표시
    document.getElementById('stockBasic_company_info').innerHTML = ""; // 초기화
    const additionalInfo = data.additional_info['additional_info'];
    let htmlContent = `<table class="stockBasicInfoTable"><caption>종목 기본 정보</caption><tbody>`;
    Object.keys(additionalInfo).forEach(key => {
        const valueWithUnit = appendUnit(key, additionalInfo[key]);
        htmlContent += `<tr><td>${key}</td><td>${valueWithUnit}</td></tr>`;
    });
    htmlContent += `</tbody></table>`;
    document.getElementById('stockBasic_company_info').innerHTML = htmlContent;

    // 연간 재무 데이터 표시
    if (data.income_statement && typeof data.income_statement === 'object') {
        const incomeStatement = data.income_statement;
        const keyMapping = {
            'Total Revenue': '총 매출액',
            'Operating Income': '영업이익',
            'Operating Margin': '영업이익률',
            'Net Income': '순이익',
            'EPS': '주당순이익'
        };
        const formatCurrency = (num) => `${(num / 100000000).toFixed(2)} 억 달러`;
        const formatEPS = (num) => `${num.toFixed(3)} 달러`;

        const titleElement = document.querySelector('.financial-title h2');
        titleElement.textContent = "연간 재무 데이터";
        let htmlContent = `<table class="stockAnnualFinancialsTable"><caption>연간 재무 데이터</caption><thead><tr><th>년도</th>`;
        Object.keys(keyMapping).forEach(key => {
            htmlContent += `<th>${keyMapping[key]}</th>`;
        });
        htmlContent += `</tr></thead><tbody>`;

        Object.keys(incomeStatement['Total Revenue']).sort().reverse().forEach(date => {
            const year = new Date(date).getFullYear();
            htmlContent += `<tr><td>${year}</td>`;
            Object.keys(keyMapping).forEach(key => {
                let value = incomeStatement[key][date];
                if (['Total Revenue', 'Operating Income', 'Net Income'].includes(key)) {
                    value = formatCurrency(value);
                } else if (key === 'Operating Margin') {
                    value = `${(value * 100).toFixed(2)}%`;
                } else if (key === 'EPS') {
                    value = formatEPS(value);
                }
                htmlContent += `<td>${value !== null ? value : '-'}</td>`;
            });
            htmlContent += `</tr>`;
        });

        htmlContent += `</tbody></table>`;
        document.getElementById('stockBasic_finance_info').innerHTML = htmlContent; // 가정: 'financialDataContainer'이 새로 만든 div의 ID
    }
    else {
        console.error('annual_data is not available or not an object');
    }
    // 차트 데이터 준비 및 차트 표시 함수 호출
    const chartData = data.charts_data;
    const processedChartData = preprocessChartData(chartData);            

    console.log(processedChartData);            
    displayAnnualFinancialsChart(processedChartData);
    displayQuarterlyGrowthChart(processedChartData);
    stockBasicContainer.style.maxHeight = stockBasicContainer.scrollHeight + 'px';

}
//분기별 매출 성장 차트 
function displayAnnualFinancialsChart(chartData) {
    var operatingMargins = chartData.annual_financials.operating_margin;
    var transformedOperatingMargins = operatingMargins.map(function(value) {
        return parseFloat((value * 100).toFixed(2)); // 100을 곱하고, 소수점 두 자리까지 반올림
    });
    Highcharts.chart('annualFinancialsChart', {
        chart: {
            zoomType: 'xy'
        },
        title: {
            text: '년도별 매출 및 영업이익 추이'
        },
        xAxis: [{
            categories: chartData.annual_financials.years,
            crosshair: true
        }],
        yAxis: [{ // Primary yAxis
            labels: {
                format: '{value}억',
                style: {
                    color: Highcharts.getOptions().colors[1]
                }
            },
            title: {
                text: '매출액 & 영업이익',
                style: {
                    color: 'black'
                }
            }
        }, { // Secondary yAxis
            title: {
                text: '영업이익률',
                style: {
                    color: 'black'
                }
            },
            labels: {
                format: '{value} %',
                style: {
                    color: Highcharts.getOptions().colors[0]
                }
            },
            opposite: true
        }],
        tooltip: {
            shared: true
        },
        series: [{
            name: '매출액',
            type: 'column',
            yAxis: 0,
            data: chartData.annual_financials.revenue.map(value => value / 1e8), // 억 달러로 변환
            tooltip: {
                valueSuffix: ' 억'
            }

        }, {
            name: '영업이익',
            type: 'column',
            yAxis: 0,
            data: chartData.annual_financials.operating_income.map(value => value / 1e8), // 억 달러로 변환
            tooltip: {
                valueSuffix: ' 억'
            }
        }, {
            name: '영업이익률(%)',
            type: 'spline',
            yAxis: 1,
            data: transformedOperatingMargins,
            color: '#FFA500', 
            tooltip: {
                valueSuffix: '%'
            }
        }]
    });
}

function displayQuarterlyGrowthChart(chartData) {
    Highcharts.chart('quarterlyGrowthChart', {
        chart: {
            zoomType: 'xy'
        },
        title: {
            text: '분기별 매출 성장 추이'
        },
        xAxis: [{
            categories: chartData.quarterly_growth.quarters,
            crosshair: true
        }],
        yAxis: [{ // Primary yAxis
            labels: {
                format: '{value}억',
                style: {
                    color: Highcharts.getOptions().colors[1]
                }
            },
            title: {
                text: '매출액',
                style: {
                    color: 'black'
                }
            }
        }, { // Secondary yAxis
            title: {
                text: '매출 성장률',
                style: {
                    color: 'black'
                }
            },
            labels: {
                format: '{value} %',
                style: {
                    color: Highcharts.getOptions().colors[0]
                }
            },
            opposite: true
        }],
        tooltip: {
            shared: true
        },
        series: [{
            name: '분기 매출액',
            type: 'column',
            yAxis: 0,
            data: chartData.quarterly_growth.revenue.map(value => value / 1e8), // 억 달러로 변환
            tooltip: {
                valueSuffix: ' 억'
            }
        }, {
            name: '매출 성장률(%)',
            type: 'spline',
            yAxis: 1,
            data: chartData.quarterly_growth.revenue_growth,
            color: '#FFA500', 
            tooltip: {
                valueSuffix: '%'
            }
        }]
    });
}
//************************************** AI가 말해주는 주식정보 함수 Ends [#3.Get StockInfo]********************************************//
//********************************* AI가 말해주는 주식정보 함수 Starts [#4.Ask AI Anything]****************************************//
function loadAiChat() {
    alert("기능 준비중입니다.");
    return
    try {
        //앞선 데이터들 모두 클리어(?!) 기획을.. 어케할지 고민
            /**
        document.getElementById('stockBasic').style.display = 'none';
        document.getElementById('fingptChartArea').style.display = 'none';
        document.getElementById('gptEarningTableArea').style.display = 'none';
        document.getElementById('gptMessageArea').style.display = 'none';
        document.getElementById('gptStockwaveArea').style.display = 'none';
        document.getElementById("stockBasic_company_info").innerHTML = "";
        document.getElementById("annualFinancialsChart").innerHTML = "";
        document.getElementById("quarterlyGrowthChart").innerHTML = "";
        document.getElementById("stockBasic_finance_info").innerHTML = ""; **/
        var aiChatStatus = document.getElementById('aiChatStatus');
        var aiStockChat = document.getElementById('aiStockChat');
    
        if (aiChatStatus.textContent === '[OFF]') {
            aiChatStatus.textContent = '[ON]';
            aiStockChat.style.backgroundImage = 'linear-gradient(to right, #4CAF50, #8BC34A)'; // ON 상태 색상
            document.querySelector('#chatTitle').scrollIntoView({ behavior: 'smooth' });
        } else {
            aiChatStatus.textContent = '[OFF]';
            aiStockChat.style.backgroundImage = 'linear-gradient(to right, #f5c263, #f58b00)'; // 원래 색상
        }
        
        // window.scrollTo(0, document.body.scrollHeight);

    }                
        catch (error) {
    }         
}
// 채팅에 설정버튼 기능
function openSettingsModal() {
    const modal = document.getElementById('settingsModal');
    const selectedOption = document.querySelector('input[name="aiOption"]:checked').value;
    modal.setAttribute('data-initial-ai-option', selectedOption); 
    modal.style.display = 'flex';
}
function closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    modal.style.display = 'none';
    const initialAiOption = modal.getAttribute('data-initial-ai-option'); 
    if (initialAiOption) {
        document.querySelector(`input[name="aiOption"][value="${initialAiOption}"]`).checked = true;
    }
}
// Save 버튼 클릭 시 변경한 라디오 선택값 저장하는거
function toggleSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal.style.display === 'none' || modal.style.display === '') {
        openSettingsModal();
    } else {
        const selectedOption = document.querySelector('input[name="aiOption"]:checked').value;
        modal.setAttribute('data-initial-ai-option', selectedOption); 
        saveClassification(selectedOption);
        modal.style.display = 'none';
    }
}
//채팅창 닫기
function closeChatApp() {
    document.getElementById('chatApp').style.display = 'none';
    const inputContainer = document.querySelector('.input-container');
    //컨텐츠들이 중간에 계속 추가되다보니, scrollTo(0,0)이 언젠가부터 안먹혀서 만듬 ㅠ
    if (inputContainer) {
        const yOffset = inputContainer.getBoundingClientRect().top + window.pageYOffset;
        window.scrollTo({top: yOffset, behavior: 'smooth'});
    } else {
        window.scrollTo({top: 0, left: 0, behavior: 'smooth'});
        console.log("Element not found.");
    }            
    loadAiChat();
}   
//라디오 버튼 선택한거에 따라 DB 저장하기   
/**************[젼역 생성]*************/
let currentSelections = [];
let tempSelections = [];
function saveClassification(selectedOption){
    // "gpt4" 선택 시 다른 선택 사항 초기화
    if (selectedOption === "gpt4") {
        // "GPT4 Talk" 선택 시 임시 배열에 현재 선택 사항을 저장하고, 중복 제거
        tempSelections = [...new Set([...currentSelections, "gpt4"])];
        currentSelections = ["gpt4"];
    } else {
        // "GPT4 Talk"가 아닌 다른 선택이 이루어지면 "gpt4"를 배열에서 제거하고, 이전 선택을 복원
        const index = currentSelections.indexOf("gpt4");
        if (index > -1) {
            currentSelections.splice(index, 1, ...tempSelections.filter(option => option !== "gpt4"));
            tempSelections = []; 
        }
        // 선택된 옵션을 배열에 추가 (이미 있으면 추가하지 않음)
        if (!currentSelections.includes(selectedOption)) {
            currentSelections.push(selectedOption);
        }
    }
    switch (selectedOption) {
        case "aiQuery":
            handleAiQuery();
            break;
        case "webBased":
            const webUrl = document.querySelector('input[name="aiOption"][value="webBased"] + input').value;
            handleWebBasedQuery(webUrl);
            break;
        case "youtubeBased":
            const youtubeUrl = document.querySelector('input[name="aiOption"][value="youtubeBased"] + input').value;
            handleYoutubeBasedQuery(youtubeUrl);
            break;
        case "googleBased":
            //handleGoogleBasedQuery();
            break;
    }
    updateCurrentMode(); 
}

function updateCurrentMode() {
    let currentText = currentSelections.map(option => {
        switch(option) {
            case "aiQuery": return "조회내용기반 Talk";
            case "webBased": return "웹사이트기반 Talk";
            case "youtubeBased": return "Youtube기반 Talk";
            case "googleBased": return "Google기반 Talk";
            default: return "";
        }
    }).join(", ");

    document.getElementById("currentModeButton").textContent = currentText ? `${currentText}` : 'GPT4 Talk';
}

//리셋버튼 클릭시
function resetClassification() {
    currentSelections = ['gpt4'];
    updateCurrentMode();
    // 모든 라디오 버튼의 체크를 해제하고, gpt4만 체크
    document.querySelectorAll('input[name="aiOption"]').forEach((input) => {
        input.checked = input.value === 'gpt4';
    });
}

//설정창 >> 1. 현재 조회된 데이터들에 대한 TALK를 위한 데이터 vectorDB 저장
function handleAiQuery() {
    const selectors = [
        "#stockBasic_company_info", "#annualFinancialsChart", "#quarterlyGrowthChart",
        "#stockBasic_finance_info", "#earningsChart", "#recommendationsChart",
        "#latest_quarter_revenue", "#revenue_yoy_percentage", "#revenue_qoq_percentage",
        "#revenue_beat_miss_ratio", "#latest_quarter_operating_income",
        "#operating_income_yoy_percentage", "#operating_income_qoq_percentage",
        "#eps_beat_miss_ratio", "#analysisResult", "#newsAnalysis", "#stockwaveChart",
        "#foreignTickerNewsArea","#fomc-press-releases"
    ];
    let markdownData = "";
    selectors.forEach(selector => {
        const element = document.querySelector(selector);
        if (element && (element.innerHTML.trim() !== "" || element.innerText.trim() !== "")) {
            // Only proceed if element has non-whitespace content
            let title = selector.replace(/#/g, "").replace(/_/g, " ").toUpperCase();
            let content = element.innerHTML.trim() || element.innerText.trim();
            markdownData += `### ${title}\n${content}\n\n`;
        }
    });
    if (markdownData.trim() !== "") {
        // Send the markdown data to the server
        document.getElementById('loading_bar_chatting').style.display = 'block';
        fetch('/rag/handle-ai-query/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ markdownData: markdownData })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Success:", data);
            if (data && data.result) {  //채팅창에 간단하게 웹사이트 설명 보여주고 시작하자
                document.getElementById('loading_bar_chatting').style.display = 'none'; 
                const responseDiv = document.createElement('div');
                responseDiv.classList.add('message', 'server');
                responseDiv.textContent = data.result; 
                document.getElementById('chatMessages').appendChild(responseDiv);
                document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
            }                
        })
        .catch(error => {
            console.error("Error:", error.message);
            document.getElementById('loading_bar_chatting').style.display = 'none'; 
        });
    } else {
        alert("주식정보 Data를 조회한 후 설정해주세요!")
        document.getElementById('loading_bar_chatting').style.display = 'none'; 
        console.log("No data to send.");
    }
}
//설정창 >> 2. 불러올 web base에 대한 vectorDB 저장
function handleWebBasedQuery(webUrl) {
    document.getElementById('loading_bar_chatting').style.display = 'block'; 
    fetch('/rag/handle-webbased-query/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: webUrl })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`handleWebBasedQuery not ok, status: ${response.status}`);
            document.getElementById('loading_bar_chatting').style.display = 'none'; 
        }
        return response.json(); 
    })
    .then(data => {
        console.log("Success:", data);
        if (data && data.result) {  //채팅창에 간단하게 웹사이트 설명 보여주고 시작하자
            document.getElementById('loading_bar_chatting').style.display = 'none'; 
            const responseDiv = document.createElement('div');
            responseDiv.classList.add('message', 'server');
            responseDiv.textContent = data.result.output_text; 
            document.getElementById('chatMessages').appendChild(responseDiv);
            document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
        }                
    })
    .catch(error => {
        console.error("Error:", error.message);
        document.getElementById('loading_bar_chatting').style.display = 'none'; 
    });
}
    //실제 메시지 입력하면, 데이터 호출해서 보여주는 함수 
    function sendChatMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'user');
    messageDiv.textContent = message;
    document.getElementById('chatMessages').appendChild(messageDiv);

    // 로딩 메시지 추가
    const loadingDiv = document.createElement('div');
    loadingDiv.classList.add('message', 'loading');
    loadingDiv.style.backgroundColor = '#FFF3CD'; // 연주황색 배경 설정
    document.getElementById('chatMessages').appendChild(loadingDiv);
    
    const loadingSpan = document.createElement('span');
    const loadingText = '열심히 답변 생성중입니다 ';
    let loadingTextIndex = 0;
    
    const loadingInterval = setInterval(() => {
        loadingSpan.textContent = loadingText.substring(0, loadingTextIndex) + '_';
        loadingTextIndex++;
        if (loadingTextIndex > loadingText.length) loadingTextIndex = 0;
    }, 150);
    
    loadingDiv.appendChild(loadingSpan);
    document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;

    console.log(message);
    
    // 'gpt4' 옵션이 선택되었는지 확인
    const isGPT4Checked = document.querySelector('input[name="aiOption"][value="gpt4"]').checked;
    const isGoogleBasedChecked = document.querySelector('input[name="aiOption"][value="googleBased"]').checked;
    let requestURL = '/rag/handle-ai-answer/'; // 기본 URL

    if (isGPT4Checked) {
        requestURL = '/rag/handle-gpt4-talk/';
    } else if (isGoogleBasedChecked) {
        requestURL = '/rag/handle-google-talk/';
    } 
    
    fetch(requestURL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        clearInterval(loadingInterval); // 로딩 텍스트 애니메이션 중지
        loadingDiv.remove(); // 로딩 메시지 제거

        const responseDiv = document.createElement('div');
        responseDiv.classList.add('message', 'server');
        responseDiv.textContent = data.result;
        document.getElementById('chatMessages').appendChild(responseDiv);
        document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
    })
    .catch(error => {
        clearInterval(loadingInterval);
        console.error('Error:', error);
    });
}
