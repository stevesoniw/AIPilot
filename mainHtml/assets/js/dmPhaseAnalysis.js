//******************************** 2nd GNB:: 국내 주식 유사국면 분석 Starts*************************************//
// 1.종목코드 불러오기(from KRX)
async function fetchStockCodes() {
    try {
        const response = await fetch('/stock-codes/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const stockCodes = await response.json();
//console.log(stockCodes); // 데이터 구조 확인을 위해 콘솔에 출력
        const selectElement = $('#stockCodeSelect'); //['케이씨티', '089150'], ['케이엔에스', '432470'] 이 형태로 반복해서옴
        selectElement.empty(); //로딩중.. 요거 메시지 제거
        stockCodes.forEach(stock => {
            let option = new Option(`${stock[0]} (${stock[1]})`, stock[1]);
            selectElement.append(option);
        });
        selectElement.select2({
            placeholder: "원하시는 종목을 검색해주세요!",
            allowClear: true,
            minimumResultsForSearch: 0 // 검색 활성화
        }).val(null).trigger("change");
    } catch (error) {
        console.error("Failed to fetch stock codes: ", error);
    }
}
// 2. 주식차트 데이터 불러오기(from yFinance)
async function fetchChartData() {
    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;
    const stockCode = document.getElementById('stockCodeSelect').value;
    //유사국면 차트 조회 후 다시 처음차트 조회하면 없애버리기 + 유사국면쪽 안보이게 리셋
    document.getElementById('stockSecondChartContainer').innerHTML = ''; 
    document.getElementById('date-select-2').style.display = 'none';
    document.getElementById('similarityResult').style.display = 'none';

    const requestBody = JSON.stringify({ stockCode, fromDate, toDate });
    document.getElementById('loading_bar_firstStock').style.display = 'block';
    try {
        const response = await fetch('/stock-chart-data', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: requestBody
        });
        if (!response.ok) throw new Error('Network response was not ok.');
        const responseData = await response.json();
        document.getElementById('loading_bar_firstStock').style.display = 'none';

console.log(responseData.chartData);

        drawChart(responseData.chartData, 1); // 차트그리기
    } catch (error) {
        document.getElementById('date-select-2').style.display = 'none';
        document.getElementById('loading_bar_firstStock').style.display = 'none';
        console.error('Error fetching stock chart data:', error);
    }
}

//3. 처음 요청한 주식차트 그리기 (Feat.HighChart)
function drawChart(chartData, num) {
    // 데이터 유효성 검사
    if (!chartData || !chartData.labels || chartData.labels.length === 0 || !chartData.datasets || chartData.datasets.some(dataset => dataset.data.length === 0)) {
        console.error('Invalid or missing chart data');
        document.getElementById('date-select-2').style.display = 'none';
        alert('차트 데이터가 유효하지 않습니다.');
        return; // 함수 종료
    }
    var container;
    if (num === 1){
        container = document.getElementById('stockFirstChartContainer');    
    }else if(num === 2){
        container = document.getElementById('stockSecondChartContainer');    
    }

    // 차트 컨테이너 존재 여부 검사
    if (!container) {
        console.error('Chart container not found');
        document.getElementById('date-select-2').style.display = 'none';
        alert('차트 컨테이너를 찾을 수 없습니다.');
        return; // 함수 종료
    }

    const financialData = chartData.labels.map((label, index) => [
        Date.parse(label), // x 값: 타임스탬프로 변환
        chartData.datasets[0].data[index], // open
        chartData.datasets[1].data[index], // high
        chartData.datasets[2].data[index], // low
        chartData.datasets[3].data[index]  // close
    ]);

    document.getElementById('date-select-2').style.display = 'block';

    // Highstock 사용하여 차트 생성
    Highcharts.stockChart(container, {
        chart: {
            backgroundColor: 'transparent'
        },
        rangeSelector: {
            selected: 1
        },
        title: {
            text: 'Stock Price Data'
        },
        series: [{
            type: 'candlestick',
            name: 'Stock Price',
            data: financialData,
            color: 'blue',
            lineColor: 'blue',
            upColor: 'red',
            upLineColor: 'red',
        }],
        events: {
            load: function() {
                container.style.display = 'block';
                container.scrollIntoView({behavior: "smooth", block: "end"});
            }
        }
    });
    container.style.display = 'block';
    container.scrollIntoView({behavior: "smooth", block: "end"});
    const spacer = document.createElement('div');
    spacer.style.height = '200px';
    document.body.appendChild(spacer);

    window.scrollTo(0, document.body.scrollHeight);;
}
//4. 유사국면 데이터 찾기 GOGO  (by son , not jay)
async function similarTimeSearch() {
    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;
    const fromDate_2 = document.getElementById('fromDate_2').value;
    const toDate_2 = document.getElementById('toDate_2').value;
    const stockCode = document.getElementById('stockCodeSelect').value;
    document.getElementById('loading_bar_secondStock').style.display = 'block';
    document.getElementById('similarityResult').style.display = 'none';

    try {
        const response = await fetch('/find-similar-period', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({stockCode, fromDate, toDate, fromDate_2, toDate_2})
        });
        if (!response.ok) throw new Error('Network response was not ok.');

        const result = await response.json();
        document.getElementById('loading_bar_secondStock').style.display = 'none';
        document.getElementById('similarityResult').style.display = 'block';

console.log(result); 

        // 결과 표시 
        const similarityResultDiv = document.getElementById('similarityResult');
        similarityResultDiv.innerHTML = `
            <span style="color: red;">[최종 선정 유사국면]   </span> 
            <span style="color: darkorange;">${result.bestPeriodStart} ~ ${result.bestPeriodEnd}   </span> 
            <span style="font-size: smaller;">  (*유사도점수 </span>
            <span style="font-size: smaller; color: darkblue;"> : ${result.dtwDistance} (Feat. DTW알고리즘))</span>
        `;
        drawChart(result.chartData.chartData, 2); //차트 그리기 함수 호출

    } catch (error) {
        document.getElementById('loading_bar_secondStock').style.display = 'none';
        console.error('Error fetching Similar chart data:', error);
    }
}
//******************************** 2nd GNB:: 국내 주식 유사국면 분석 Ends*************************************//