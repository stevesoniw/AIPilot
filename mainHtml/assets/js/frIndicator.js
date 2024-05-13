//******************************** 글로벌 주요경제지표 함수 [#1.핵심지표] Starts ***********************************// 

/** 서버에서 이미지 만들어서 base64로 받아오는 형태 [차트가 안예뻐서 일단 보류]
async function loadEconomicIndicators() {
    try {
        document.getElementById('loading_bar_economics').style.display = 'block';

        const response = await fetch('/api/economic-indicators');
        const data = await response.json();

        document.getElementById('economicChartArea').style.display = 'block';
        document.getElementById('economicIndicators').src = 'data:image/png;base64,' + data.economic_indicators_chart;
        document.getElementById('loading_bar_economics').style.display = 'none';

    } catch (error) {
        console.error('Error loading loadEconomicIndicators data:', error);
        document.getElementById('loading_bar_economics').style.display = 'none';                 
        document.getElementById('economicChartArea').style.display = 'none';             
    }     
}**/
async function fetchAndDisplayIndicators() {
    try {
        const form = document.getElementById('indicatorForm');
        const formData = new FormData(form);
        const selectedIndicators = formData.getAll('indicators');
        document.getElementById('loading_bar_economics').style.display = 'block';

        if (selectedIndicators.length === 0) {
            alert('Please select at least one indicator before proceeding.');
            document.getElementById('loading_bar_economics').style.display = 'none'; 
            return; 
        }        

        // 각 인디케이터에 대해 파일에서 데이터를 읽어옴
        const promises = selectedIndicators.map(async (series_id) => {
            const response = await fetch(`/batch/fred_indicators/${series_id}.json`);
            const data = await response.json();
            const textDataResponse = await fetch(`/batch/fred_indicators/${series_id}_aitalk.txt`);
            const textData = await textDataResponse.text();            
            return { series_id, data , textData};
        });

        // 모든 데이터를 한꺼번에 가져옴
        const results = await Promise.all(promises);

        document.getElementById('loading_bar_economics').style.display = 'none';
        const chartAnalysisArea = document.getElementById('chart-anal-area');
        const chartContainer = document.getElementById('chartContainer');

        if (results.length > 0) {
            document.getElementById('chartAnalysis').innerHTML = "";
            chartAnalysisArea.style.display = 'block';
            chartContainer.style.display = 'block';

            // 차트 렌더링
            renderHighchart(results);
            results.forEach(({ series_id, textData }) => {
                const chartAnalysisElement = document.createElement('div');
                textData = textData.replace(/\*\*(.*?)\*\*/g, '<span style="color: #ff1480; text-transform: uppercase;">$1</span>');
                textData = textData.replace(/- \s*/g, '<br>');
                textData = textData.replace(/###\s*/g, '<br><br>');
                textData = textData.replace(/(\d+\.\s+)/g, '<br>$1');
                chartAnalysisElement.innerHTML = textData;
                document.getElementById('chartAnalysis').appendChild(chartAnalysisElement);
            });           
            
        } else {
            chartAnalysisArea.style.display = 'none';
            chartContainer.style.display = 'none';
            document.getElementById('chartContainer').innerHTML = '<p>No data available</p>';
        }
    } catch (error) {
        console.error('Error loading economic indicators data:', error);
        document.getElementById('loading_bar_economics').style.display = 'none';
        chartContainer.style.display = 'none';
    }
}

function renderHighchart(datasets) {
    const indicators = {
        "DGS10": {"name": "미국채 10년이자율", "engname": "Treasury Yield"},
        "DGS2": {"name": "미국채 2년이자율", "engname": "Treasury Yield"},
        "DGS3MO": {"name": "미국채 3개월이자율", "engname": "Treasury Yield"},
        "CPIAUCSL": {"name": "미국 소비자물가지수", "engname": "Consumer Price Index"},
        "PCEPI": {"name": "미국 개인소비지출지수", "engname": "Personal Consumption Expenditures"},
        "PPIFID": {"name": "미국 생산자물가지수", "engname": "Producer Price Index"},
        "DFEDTARU": {"name": "미국 연방기금금리", "engname": "Federal Funds Rate"},
        "CSUSHPISA": {"name": "미국 주택가격지수", "engname": "Housing Price Index"},
        "GDPC1": {"name": "미국 실질국내총생산", "engname": "GDP"},
        "ECIWAG": {"name": "미국 고용비용지수", "engname": "Employment Cost Index"},
        "STLFSI4": {"name": "미국 금융스트레스지수", "engname": "Financial Stress Index"},
        "NGDPSAXDCUSQ": {"name": "미국 명목 국내총생산", "engname": "GDP"},
        "DCOILBRENTEU": {"name": "crude oil 가격", "engname": "Crude Oil Price"},
        "GFDEGDQ188S": {"name": "미국 GDP 대비 공공부채 비율", "engname": "Public Debt"},
        "MEHOINUSA672N": {"name": "미국 실질 중위 가구소득", "engname": "Real Median Household Income"},
        "INDPRO": {"name": "미국 산업생산지수", "engname": "Industrial Production Index"},
        "SP500": {"name": "S&P500 지수", "engname": "S&P 500"},
        "UNRATE": {"name": "미국 실업률", "engname": "Unemployment Rate"},
        "FEDFUNDS": {"name": "미국 금리", "engname": "interest rate"}
    }   
     
    const selectedEngNames = datasets.map(dataset => indicators[dataset.series_id].engname);    
    let series = [];
    // 각 데이터셋에서 데이터 처리
    datasets.forEach((dataset) => {
        const data = dataset.data.map((entry) => {
            const date = new Date(entry.date).getTime(); // timestamp로 변환
            let value = entry.value;
            // 값이 "NaN"인 경우 null로 처리
            value = value === "NaN" ? null : parseFloat(value);
            return [date, isNaN(value) ? null : value]; 
        }).filter((entry) => entry[1] !== null); // null인 항목 제거


        if (data.length > 0) {
            series.push({
                name: indicators[dataset.series_id].name,
                data: data,
            });
        }
    });
    // 차트 렌더링
    Highcharts.chart('chartContainer', {
        chart: {
            type: 'line',
            zoomType: 'x', // x축 방향으로만 확대/축소 가능            
        },
        title: {
            text: 'Economic Indicators Over Time',
        },
        xAxis: {
            type: 'datetime',
        },
        yAxis: {
            title: {
                text: 'Value',
            },
        },
        legend: {
            layout: 'vertical',
            align: 'right',
            verticalAlign: 'middle',
        },
        series: series,
    });
    console.log(selectedEngNames);
}


function clearData() {
    // 모든 체크박스 선택 해제
    document.querySelectorAll('#indicatorForm input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
    });

    // 차트 데이터 클리어 (Chart.js 인스턴스가 있다면)
    if (window.myEconomicChart) {
        window.myEconomicChart.destroy(); // 차트 인스턴스를 파괴하여 클리어
    }
    document.getElementById('chartContainer').style.display = 'none';
    document.getElementById('chart-anal-area').style.display = 'none';            
    document.getElementById('chartAnalysis').innerText = "";            
}        

//****************************** 글로벌 주요경제지표 함수 [#1.핵심지표] Ends *******************************// 
//****************************** 글로벌 주요경제지표 함수 [#2.indicators 분석] Start ******************************// 
//고유상품전략팀에서 요청한 예시 차트들 보여주기 (*차트+GPT토크)
async function fetchIndicatorAnal() {
    const selectBox = document.getElementById("indicator_select");
    const selectedValue = selectBox.value;
    if (selectedValue === "") {
        document.getElementById("fred_anal_area").innerHTML = "";
        return;
    }

    const image = `/batch/fred_indicators/${selectedValue}_chart.png`;
    const txt = `/batch/fred_indicators/${selectedValue}_gpt4.txt`;

    fetch(image).then(response => {
        if (response.ok) {
            const imgElement = `<img src="${image}" alt="${selectedValue}" class="fred_indicator_img">`;
            document.getElementById("fred_chart_area").innerHTML = imgElement;
        } else {
            throw new Error('Image not found');
        }
    }).catch(error => {
        console.error("Error loading image:", error);
        document.getElementById("fred_chart_area").innerHTML = "Image not available.";
    });

    fetch(txt).then(response => response.text()).then(text => {
        const textArea = document.getElementById("fred_anal_area");
        let formatData = text.replace(/\*\*(.*?)\*\*/g, '<span class="fred_anal_highlight">$1</span>');
        formatData = formatData.replace(/###/g, '■');
        if (textArea) {
            textArea.innerHTML = `<pre class="fred_indicator_text">${formatData}</pre>`;
        } else {
            console.error("Text area element not found");
        }
    }).catch(error => {
        console.error("Error loading text:", error);
        document.getElementById("fred_anal_area").innerHTML = "Analysis text not available.";
    });
}

//뉴스검색을 위해 날짜를 timestamp로 변환 (seekingalpha 인풋값이 timestamp다)
function convertDateToTimestamp(dateString) {
    var date = new Date(dateString);
    // 타임스탬프 반환 (밀리초 단위)
    var timestamp = date.getTime();
    return timestamp / 1000;
}

//indicators 뉴스 가져오기
async function fetchIndicatorNews() {
    try{
        document.getElementById('loading_bar_indicatorNews').style.display = 'block';
        const fromDate = document.getElementById('indicatorFromDate').value;
        const toDate = document.getElementById('indicatorToDate').value;   
        
        const fromTimestamp = convertDateToTimestamp(fromDate);
        const toTimestamp = convertDateToTimestamp(toDate);
        const response = await fetch(`/indicator-news`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                from_date: fromTimestamp, // 클라이언트에서 fromDate -> from_date 로 변경
                to_date: toTimestamp // 클라이언트에서 toDate -> to_date 로 변경
            }),
        });
        const indicatorNews = await response.json();
    
        document.getElementById('loading_bar_indicatorNews').style.display = 'none';

        console.log(indicatorNews);
        console.log(Array.isArray(indicatorNews)); 

        if (!Array.isArray(indicatorNews)) {
            console.error('Expected an array but received:', indicatorNews);
            return; // Exit if not an array to prevent further errors
        }
        const indicatorNewsContainer = document.getElementById('indicator_news_div');

        if (indicatorNews.length === 0) {
            // 뉴스 데이터가 없을 경우 표시할 메시지
            const noNewsMessage = document.createElement('div');
            noNewsMessage.textContent = '관련 뉴스가 없습니다.';
            noNewsMessage.className = 'no-news-message'; // 스타일 적용을 위한 클래스 추가
            indicatorNewsContainer.appendChild(noNewsMessage);
        } else {

            indicatorNewsContainer.innerHTML = ''; // 기존 내용을 지우고 새로운 뉴스로 업데이트
            indicatorNews.forEach(news => {
                const newsDiv = document.createElement('div');
                newsDiv.className = 'indicatorNews-container';
    
                const imageUrl = news.gettyImageUrl || "/static/assets/images/nature.jpg"; // Default image
                const image = document.createElement('img');
                image.src = imageUrl;
                image.alt = "News Image";
                image.className = 'indicatorNews-image';
    
                const title = document.createElement('div');
                title.className = 'indicatorNews-title';
                title.innerHTML = news.title; // Safe assuming backend sanitizes input
    
                const date = document.createElement('div');
                date.className = 'indicatorNews-date';
                date.textContent = new Date(news.publishOn).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
    
                const content = document.createElement('div');
                content.className = 'indicatorNews-content';
                content.innerHTML = news.content; // Assuming content is cleaned from malicious tags on the server-side
    
                const translateButton = document.createElement('button');
                translateButton.textContent = '한국어로 번역하기';
                translateButton.className = 'translate-button';
                translateButton.onclick = () => translateNewsContent(newsDiv); // Function to handle translation
    
                newsDiv.appendChild(image);
                newsDiv.appendChild(title);
                newsDiv.appendChild(date);
                newsDiv.appendChild(content);
                newsDiv.appendChild(translateButton);
    
                indicatorNewsContainer.appendChild(newsDiv);
            });
        }
    }catch (error) {
            console.error('Error loading fetchAndDisplayIndicatorNews');
            document.getElementById('loading_bar_indicatorNews').style.display = 'none';
    }
}

function translateNewsContent(newsDiv) {
    const title = newsDiv.querySelector('.indicatorNews-title').textContent;
    const content = newsDiv.querySelector('.indicatorNews-content').innerHTML;

    const loadingText = document.createElement('div');
    loadingText.className = 'loading-text';
    loadingText.textContent = '데이터 로딩중입니다...';
    newsDiv.appendChild(loadingText);

    fetch('/translate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title, content})
    })
    .then(response => response.json())
    .then(data => {
        newsDiv.querySelector('.indicatorNews-title').textContent = data.title;
        newsDiv.querySelector('.indicatorNews-content').innerHTML = data.content;
        loadingText.remove();
    })
    .catch(error => {
        console.error('Translation error:', error);
        loadingText.textContent = 'Translation failed.';
    });
}
//****************************** 글로벌 주요경제지표 함수 [#2.indicators 뉴스] Ends ******************************// 