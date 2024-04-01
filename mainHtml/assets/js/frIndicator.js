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
        const aiOpinionCheck = document.getElementById('aiOpinionCheck').checked;

        document.getElementById('loading_bar_economics').style.display = 'block';

        const url = `/api/economic-indicators?indicators=${selectedIndicators.join(',')}&aiOpinion=${aiOpinionCheck}`;
        const response = await fetch(url);
        const data = await response.json();
        document.getElementById('loading_bar_economics').style.display = 'none';

        // 차트 및 분석 데이터의 표시 여부를 결정
        const chartContainer = document.getElementById('chartContainer');
        const chartAnalysisArea = document.getElementById('chart-anal-area');
        if (data && data.datasets.length > 0) {
            chartContainer.style.display = 'block';
            if(data.chart_talk){
                chartAnalysisArea.style.display = 'block';
                document.getElementById('chartAnalysis').innerText = data.chart_talk;
            }else{
                chartAnalysisArea.style.display = 'none';
            }
        } else {
            chartContainer.style.display = 'none';
            chartAnalysisArea.style.display = 'none';
        }

        const backgroundColors = [
        'rgba(255, 99, 132, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgba(255, 206, 86, 0.2)',
        'rgba(75, 192, 192, 0.2)',
        'rgba(153, 102, 255, 0.2)',
        'rgba(255, 159, 64, 0.2)'
        ];
        const borderColors = [
            'rgba(255,99,132,1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)'
        ];
        const indicatorLabels = {
            "CPIAUCSL": "소비자물가지수 (CPI)",
            "PCEPI": "개인소비지출 (PCE)",
            "PPIFID": "생산자물가지수 (PPI)",
            "DFEDTARU": "연방기금금리",
            "CSUSHPISA": "주택가격지수",
            "A191RL1Q225SBEA": "실질 국내총생산 (GDP)"
        };

        // 데이터셋 설정
        const transformedDatasets = data.datasets.map((dataset, i) => ({
            ...dataset,
            data: dataset.data.map((value, index) => ({ t: data.labels[index], y: value })),
            backgroundColor: backgroundColors[i % backgroundColors.length],
            borderColor: borderColors[i % borderColors.length],
            borderWidth: 3,
            pointBackgroundColor: borderColors[i % borderColors.length],
            pointBorderColor: "#fff",
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: borderColors[i % borderColors.length],
            pointRadius: 5,
            pointHoverRadius: 7,
            label: indicatorLabels[dataset.label] || dataset.label,
            fill: false,
            spanGaps: true,
        }));
        

        // 차트 생성
        const ctx = document.getElementById('myEconomicChart').getContext('2d');
        if (window.myEconomicChart instanceof Chart) {
            window.myEconomicChart.destroy();
        }
        window.myEconomicChart = new Chart(ctx, {
            type: 'line',
            data: { datasets: transformedDatasets },
            options: {
                responsive: true,
                spanGaps: true,
                title: { display: true, text: 'Economic Indicators Over Time' },
                scales: {
                    xAxes: [{ type: 'time', time: { parser: 'YYYY-MM-DD', tooltipFormat: 'll', unit: 'day',
                                                        displayFormats: {
                                                            day: 'MMM D, YYYY',
                                                            month: 'MMM YYYY',
                                                            year: 'YYYY'
                                                        }
                                                    },
                                scaleLabel: { display: true, labelString: 'Date' },
                                ticks: {
                                    autoSkip: true,
                                    maxTicksLimit: 20 // X축에 표시할 최대 눈금 수를 조정하여 레이블이 겹치지 않도록 함
                                }
                            }],
                    yAxes: [{ ticks: { beginAtZero: false }, scaleLabel: { display: true, labelString: 'Value' } }]
                },
                legend: { position: 'top' },
                tooltips: { mode: 'index', intersect: false },
                hover: { mode: 'nearest', intersect: true }
            }
        });
    } catch (error) {
        console.error('Error loading economic indicators data:', error);
        document.getElementById('loading_bar_economics').style.display = 'none';
    }
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
//****************************** 글로벌 주요경제지표 함수 [#2.채권가격] Start ******************************// 

async function fetchBondsData() {
    // 'bonds_chart_div'에 이미 차트 데이터가 있으면 요청 중단(=메뉴이동 시에 한번 호출한적 있으면 하지말자)
    const bondsChartDiv = document.getElementById('bonds_chart_div');
    if (Plotly.d3.select(bondsChartDiv).select('.plot-container').node()) {
        // 차트가 이미 그려져 있다면 함수 종료
        console.log('Chart already drawn. Skipping fetch.');
        return;
    }
    try {
        // 'loading_bar_bonds'을 표시
        document.getElementById('loading_bar_bonds').style.display = 'block';

        // 서버에서 차트 구성 데이터와 레이아웃 설정을 가져오기
        const response = await fetch('/get_bonds_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        // JSON으로 데이터 변환
        const data = await response.json();
        
        // 기준금리 차트 데이터 및 레이아웃 설정
        const baseRateData = data.base_rate_chart.data;
        const baseRateLayout = data.base_rate_chart.layout;

        // 이자율 차트 데이터 및 레이아웃 설정
        const interestRateData = data.interest_rate_chart.data;
        const interestRateLayout = data.interest_rate_chart.layout;
        
        // Plotly 차트를 생성
        Plotly.newPlot('bonds_chart_div', baseRateData, baseRateLayout);
        Plotly.newPlot('interest_chart_div', interestRateData, interestRateLayout);
        // 'loading_bar_bonds' 숨기기
        document.getElementById('loading_bar_bonds').style.display = 'none';
        var bondArea = document.getElementById('bond-area').style.display = 'block';
    }catch (error) {
        console.error('Error loading fetchBondsData(chart):', error);
        document.getElementById('loading_bar_bonds').style.display = 'none';
    }
    
}

//채권 뉴스 가져오기
async function fetchAndDisplayBondsNews(category) {
    try{
        document.getElementById('loading_bar_bondsNews').style.display = 'block';
        const response = await fetch(`/bond-news/${category}`);
        const bondNews = await response.json();
    
        document.getElementById('loading_bar_bondsNews').style.display = 'none';

        console.log(bondNews);

        const bondsNewsContainer = document.getElementById('bonds_news_div');

        if (bondNews.length === 0) {
            // 뉴스 데이터가 없을 경우 표시할 메시지
            const noNewsMessage = document.createElement('div');
            noNewsMessage.textContent = '관련 뉴스가 없습니다.';
            noNewsMessage.className = 'no-news-message'; // 스타일 적용을 위한 클래스 추가
            bondsNewsContainer.appendChild(noNewsMessage);
        } else {

            bondsNewsContainer.innerHTML = ''; // 기존 내용을 지우고 새로운 뉴스로 업데이트
            bondNews.forEach(news => {
                const newsDiv = document.createElement('div');
                newsDiv.className = 'bondNews-container';

                console.log(news.title)
                const imageUrl = news.gettyImageUrl || "/static/assets/images/nature.jpg"; // 기본 이미지 경로 설정
                const image = document.createElement('img');
                image.src = imageUrl;
                image.alt = "News Image";
                image.className = 'bondNews-image';
        
                const title = document.createElement('div');
                title.className = 'bondNews-title';
                title.textContent = news.title;
        
                const content = document.createElement('div');
                content.className = 'bondNews-content';
                content.innerHTML = news.content; 

                // '한국어로 번역하기' 버튼 추가
                const translateButton = document.createElement('button');
                translateButton.textContent = '한국어로 번역하기';
                translateButton.className = 'translate-button'; // 스타일 적용을 위한 클래스 추가

                translateButton.addEventListener('click', function() {
                    const newsItem = this.parentNode; // 뉴스 항목의 컨테이너 참조
                    const newsTitle = newsItem.querySelector('.bondNews-title').textContent;
                    const newsContent = newsItem.querySelector('.bondNews-content').innerHTML;
                
                    // 로딩바 HTML 문자열
                    const loadingBarHtml = `
                        <div id="loading_bar_bondsTranslate" class="loading_bar_translate">
                            <img src="/static/assets/images/LoadingBar_A.gif">
                            <p class="loading-text">데이터 로딩중입니다.</p>
                        </div>`;
                
                    // 로딩바를 뉴스 항목에 추가
                    newsItem.insertAdjacentHTML('beforeend', loadingBarHtml);
                    const loadingBar = newsItem.querySelector('.loading_bar_translate');
                    loadingBar.style.display = 'block'; // 로딩바 표시
                
                    fetch('/translate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ title: newsTitle, content: newsContent })
                    })
                    .then(response => response.json())
                    .then(data => {
                        // 번역된 내용으로 업데이트
                        newsItem.querySelector('.bondNews-title').textContent = data.title;
                        newsItem.querySelector('.bondNews-content').innerHTML = data.content;
                        
                        // 로딩바 제거
                        loadingBar.style.display = 'none'; 
                        loadingBar.remove();
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        // 오류 발생 시 로딩바도 제거
                        loadingBar.style.display = 'none';
                        loadingBar.remove();
                    });
                });
            
        
                newsDiv.appendChild(image);
                newsDiv.appendChild(translateButton);                     
                newsDiv.appendChild(title);
                newsDiv.appendChild(content);

                bondsNewsContainer.appendChild(newsDiv);
            });
        }
    }catch (error) {
            console.error('Error loading fetchAndDisplayBondsNews[news]:', error);
            document.getElementById('loading_bar_bondsNews').style.display = 'none';
    }
}
//****************************** 글로벌 주요경제지표 함수 [#2.채권가격] Ends ******************************// 