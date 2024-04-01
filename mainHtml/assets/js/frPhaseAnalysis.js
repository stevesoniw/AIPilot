//****************************** [1ST GNB][7TH MENU]유사국면 함수 Starts *******************************//  
function updateSliderValue() {
    document.getElementById('nStepsValue').textContent = document.getElementById('similarity-nSteps').value;
}       
function generateSimilarityHighCharts(chartDataArray, containerId) {
    let container = document.getElementById(containerId);
    if (!container) {
        console.error('Container not found:', containerId);
        return;
    }
    let chartTitle = '';
    if (containerId === 'similarityOriginalChartContainer') {
        chartTitle = 'Original Comparison';
    } else if (containerId === 'similarityAlignedChartContainer') {
        chartTitle = 'Aligned Comparison';
    }
    
    // nStepsValue 값 처리
    const nStepsValue = parseInt(document.getElementById('nStepsValue').textContent, 10);
    const maxXValue = Math.max(...chartDataArray.flatMap(dataset => dataset.x));
    const plotLineValue = maxXValue - nStepsValue;
    
    Highcharts.chart(containerId, {
        chart: {
            type: 'line',
            zoomType: 'x' // 줌 기능 활성화
        },
        title: {
            text: chartTitle
        },
        xAxis: {
            type: 'linear',
            title: {
                text: 'Index'
            },
            labels: {
                enabled: true // x축 라벨 활성화
            },
            plotLines: [{
                color: 'red', // 점선그리자. n-step ㅋ
                dashStyle: 'Dash', 
                value: plotLineValue, 
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
        series: chartDataArray.map(dataset => ({
            name: dataset.name,
            data: dataset.y
        })),
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

function generateSimilarityAnalysis() {
    const selectedData = document.getElementById('similarity-selectedData').value;
    const targetDateStart = document.getElementById('similarity-targetDateStart').value;
    const targetDateEnd = document.getElementById('similarity-targetDateEnd').value;
    const compareDateStart = document.getElementById('similarity-compareDateStart').value;
    const compareDateEnd = document.getElementById('similarity-compareDateEnd').value;
    const nSteps = document.getElementById('similarity-nSteps').value;

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }
    document.getElementById('loading_bar_similarity').style.display = 'block';                                
    fetch('/similarity/univariate-analyze/', {
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
            n_steps: parseInt(nSteps, 10),
        }),
    })
    .then(response => response.json())
    .then(data => {
        const originalChartData = JSON.parse(data.chart_data.original).data;
        const alignedChartData = JSON.parse(data.chart_data.aligned).data;
        document.getElementById('loading_bar_similarity').style.display = 'none';    
        // 차트 생성 함수 호출
        generateSimilarityHighCharts(originalChartData, 'similarityOriginalChartContainer');
        generateSimilarityHighCharts(alignedChartData, 'similarityAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching similarity data:', error);
        document.getElementById('loading_bar_similarity').style.display = 'none'; 
    });
    
}

//********************************* [1ST GNB][7TH MENU]유사국면 함수 Ends ***************************************//   