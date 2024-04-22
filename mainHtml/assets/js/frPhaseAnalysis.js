//****************************** [1ST GNB][7TH MENU]유사국면 함수 Starts *******************************//  
function openSimTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("similarity-tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none"; 
    }
    tablinks = document.getElementsByClassName("similarity-tab-link");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].classList.remove("active"); 
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.classList.add("active"); 
}

function updateValue(inputId, outputId) {
    document.getElementById(outputId).textContent = document.getElementById(inputId).value;
}

function generateSingleHighCharts(chartDataArray, containerId) {
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
    const nStepsValue = parseInt(document.getElementById('nSingleStepValue').textContent, 10);
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
    const nSteps = document.getElementById('single-nSteps').value;
    const nGraphs = document.getElementById('single-nGraphs').value;

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }
    console.log("Sending data:", { selectedData, targetDateStart, targetDateEnd, nSteps, nGraphs });

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
            n_graphs: parseInt(nGraphs, 10),
            n_steps: parseInt(nSteps, 10)
            //n_graphs: parseInt(nGraphs, 10)
        }),
    })
    .then(response => response.json())
    .then(data => {
        const originalChartData = JSON.parse(data.chart_data.original).data;
        const alignedChartData = JSON.parse(data.chart_data.aligned).data;
        document.getElementById('loading_bar_similarity').style.display = 'none';    
        // 차트 생성 함수 호출
        generateSingleHighCharts(originalChartData, 'similarityOriginalChartContainer');
        generateSingleHighCharts(alignedChartData, 'similarityAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching similarity data:', error);
        document.getElementById('loading_bar_similarity').style.display = 'none'; 
    });
    
}

function generateMultiAnalysis() {
    const selectedData = document.getElementById('multi-selectedData').value;
    const targetDateStart = document.getElementById('multi-targetDateStart').value;
    const targetDateEnd = document.getElementById('multi-targetDateEnd').value;
    const compareDateStart = document.getElementById('multi-compareDateStart').value;
    const compareDateEnd = document.getElementById('multi-compareDateEnd').value;
    const nSteps = document.getElementById('multi-nSteps').value;
    const nGraphs = document.getElementById('multi-nGraphs').value;

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }

    //console.log("Sending data:", JSON.stringify(payload));

    document.getElementById('loading_bar_similarity').style.display = 'block';                                
    fetch('/similarity/multivariate-analyze/', {
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
            n_steps: parseInt(nSteps, 10)
        }),        
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.chart_data.original);
        const originalChartData = data.chart_data.original;
        const alignedChartData = data.chart_data.aligned;
        document.getElementById('loading_bar_similarity').style.display = 'none';    
        // Invoke the chart creation functions
        generateMultiHighCharts(originalChartData, 'multiOriginalChartContainer');
        generateMultiHighCharts(alignedChartData, 'multiAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching similarity data:', error);
        document.getElementById('loading_bar_similarity').style.display = 'none'; 
    });
}

function formatDateWithoutTime(dateTimeStr) {
    return dateTimeStr.split(' ')[0]; 
}
function generateMultiHighCharts(chartData, containerId) {
    let container = document.getElementById(containerId);
    if (!container) {
        console.error('Container not found:', containerId);
        return;
    }
    let chartTitle = '';
    if (containerId === 'multiOriginalChartContainer') {
        chartTitle = 'Original Comparison';
    } else if (containerId === 'multiAlignedChartContainer') {
        chartTitle = 'Aligned Comparison';
    }
    const nStepsValue = parseInt(document.getElementById('nMultiStepValue').textContent, 10);
    let plotLinePosition = null;

    const formattedSeries = chartData.series.map(series => {
        if (series.name.startsWith('Graph')) {
            const nameParts = series.name.split(': ');
            const dateRangeParts = nameParts[1].split(' to ');
            const formattedStart = formatDateWithoutTime(dateRangeParts[0]);
            const formattedEnd = formatDateWithoutTime(dateRangeParts[1]);
            series.name = `${nameParts[0]}: ${formattedStart} to ${formattedEnd}`;
        }
        return series;
    });

    // Find the last index from the target series data
    if (chartData.series[0] && chartData.series[0].name.startsWith('Target:')) {
        const targetSeriesData = chartData.series[0].data;
        plotLinePosition = targetSeriesData.length - 1 - nStepsValue; // Calculate position from end with nSteps back
    }
    Highcharts.chart(containerId, {
        chart: {
            type: 'line',
            zoomType: 'x'
        },
        title: {
            text: chartTitle
        },
        xAxis: {
            categories: chartData.xAxis.categories,
            title: {
                text: 'Date'
            },
            crosshair: true,
            plotLines: [{
                color: 'red',
                value: plotLinePosition,
                dashStyle: 'Dash', 
                width: 2,
                zIndex: 5,
                label: {
                    text: 'N Steps',
                    style: {
                        color: 'red'
                    }
                }
            }]
        },
        yAxis: {
            title: {
                text: 'Value'
            }
        },
        tooltip: {
            shared: true,
            valueSuffix: ' units'
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
        series: formattedSeries,
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


//********************************* [1ST GNB][7TH MENU]유사국면 함수 Ends ***************************************//   