//****************************** [4TH GNB][2ND MENU]유사국면-마켓지수 함수 Starts *******************************//  
function generateMarketIndexAnalysis() {
    const selectedData = document.getElementById('marketindex-selectedData').value;
    const targetDateStart = document.getElementById('marketindex-targetDateStart').value;
    const targetDateEnd = document.getElementById('marketindex-targetDateEnd').value;
    const compareDateStart = document.getElementById('marketindex-compareDateStart').value;
    const compareDateEnd = document.getElementById('marketindex-compareDateEnd').value;
    const nSteps = document.getElementById('marketindex-nSteps').value;
    const nGraphs = document.getElementById('marketindex-nGraphs').value;

    if (!selectedData) {
        alert('종목을 먼저 선택해주세요!');
        return;
    }

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }

    //console.log("Sending data:", JSON.stringify(payload));

    document.getElementById('loading_bar_marketindex').style.display = 'block';                                
    fetch('/similarity/foreign-stock-analyze/', { //해외주식 유사국면 fast api 공동사용
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            selected_data: selectedData,
            target_date_start: targetDateStart,
            target_date_end: targetDateEnd,
            compare_date_start: compareDateStart,
            compare_date_end: compareDateEnd,
            n_graphs: parseInt(nGraphs, 10),
            n_steps: parseInt(nSteps, 10),
            threshold : 0.5
        }),        
    })
    .then(response => response.json().then(data => {
        if (!response.ok) {
            // 에러 메시지가 포함된 응답 처리
            throw new Error(data.detail || "An error occurred");
        }
        return data;  // 성공 응답 데이터 반환
    }))
    .then(data => {
        console.log(data.chart_data.original);
        console.log(data.chart_data.aligned);
        //const originalChartData = data.chart_data.original;
        //const alignedChartData = data.chart_data.aligned;
        const originalChartData = JSON.parse(data.chart_data.original);
        const alignedChartData = JSON.parse(data.chart_data.aligned);
        document.getElementById('loading_bar_marketindex').style.display = 'none';    

        generateMarketIndexHighCharts(originalChartData, 'marketIndexOriginalChartContainer');
        generateMarketIndexHighCharts(alignedChartData, 'marketIndexAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching marketindex data:', error.message);
        alert(error.message);  // 서버 에러 메시지 또는 기본 에러 메시지를 alert로 표시
        document.getElementById('loading_bar_marketindex').style.display = 'none'; 
    });
}

function generateMarketIndexHighCharts(chartDataArray, containerId) {
    let container = document.getElementById(containerId);
    if (!container) {
        console.error('Container not found:', containerId);
        return;
    }

    if (!chartDataArray || !chartDataArray.series) {
        alert('해당 종목의 차트데이터가 존재하지 않습니다.');
        return;
    }    
    let chartTitle = '';
    if (containerId === 'marketIndexOriginalChartContainer') {
        chartTitle = 'Original Comparison';
    } else if (containerId === 'marketIndexAlignedChartContainer') {
        chartTitle = 'Aligned Comparison';
    }
    const nStepsValue = parseInt(document.getElementById('nMarketIndexStepValue').textContent, 10);
    const categories = chartDataArray.xAxis.categories;
    const maxXValue = chartDataArray.xAxis.categories.length - 1;
    const longestSeriesLength = Math.max(...chartDataArray.series.map(series => series.data.length));
    const plotLineValue = longestSeriesLength - nStepsValue - 1;

    const allSeries = chartDataArray.series.map((series, index) => {
        if (index === 0) { 
            series.data = series.data.slice(0, plotLineValue + 1);
        }
        if (series.name.startsWith('Graph')) {
            const nameParts = series.name.split(': ');
            const dateRangeParts = nameParts[1].split(' to ');
            const formattedStart = formatDateWithoutTime(dateRangeParts[0]);
            const formattedEnd = formatDateWithoutTime(dateRangeParts[1]);
            series.name = `${nameParts[0]}: ${formattedStart} to ${formattedEnd}`;
        }
        return series;
    });

    Highcharts.chart(containerId, {
        chart: {
            type: 'line',
            zoomType: 'x'
        },
        title: {
            text: chartTitle
        },
        xAxis: {
            type: 'linear',
            categories: categories,
            title: {
                text: 'Index'
            },
            labels: {
                enabled: true
            },           
            crosshair: true,
            plotLines: [{
                color: 'red',
                value: plotLineValue, 
                dashStyle: 'Dash', 
                width: 2,
                label: {
                    text: 'N Steps'
                }
            }]
        },
        yAxis: {
            title: {
                text: 'Value'
            }
        },
        legend: {
            layout: 'vertical',
            align: 'right',
            verticalAlign: 'middle'
        },
        plotOptions: {
            series: {
                label: {
                    connectorAllowed: false
                },
                pointStart: 0
            }
        },
        series: allSeries,
        responsive: {
            rules: [{
                condition: {
                    maxWidth: 500
                },
                chartOptions: {
                    legend: {
                        layout: 'horizontal',
                        align: 'center',
                        verticalAlign: 'bottom'
                    }
                }
            }]
        }
    });
}


//****************************** [4TH GNB][2ND MENU]유사국면-마켓지수 함수 Ends *******************************//  