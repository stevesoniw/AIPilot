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

/*************  유사국면분석 (단일지표)  ****************/
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

/*************  유사국면분석 (복수지표)  ****************/

function generateMultiHighCharts(chartDataArray, containerId) {
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
    
    // nStepsValue 값 처리
    const nStepsValue = parseInt(document.getElementById('nMultiStepValue').textContent, 10);
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

function appendSelectedData() {
    const selectBox = document.getElementById('multi-selectedData');
    const weightsBox = document.getElementById('multi-nWeights');
    const selectedValue = selectBox.value;
    const selectedWeight = weightsBox.value;
    const container = document.getElementById('selectedDataContainer');

    const item = document.createElement('div');
    item.className = 'multi-select-item';
    //weight는 일단 hidden
    const weightInput = document.createElement('input');
    weightInput.type = 'hidden';
    weightInput.value = selectedWeight;
    weightInput.className = 'multi-select-weight';    

    const text = document.createElement('input');
    text.type = 'text';
    text.className = 'multi-select-text';
    text.value = selectedValue;
    text.readOnly = true;

    const deleteBtn = document.createElement('span');
    deleteBtn.className = 'multi-select-delete';
    deleteBtn.innerHTML = 'x';
    deleteBtn.onclick = function() {
        container.removeChild(item);
    };

    item.appendChild(text);
    item.appendChild(weightInput);
    item.appendChild(deleteBtn);
    container.appendChild(item);
}

function generateMultiAnalysis() {
    const dataContainer = document.getElementById('selectedDataContainer');
    const allInputs = dataContainer.querySelectorAll('.multi-select-text');
    const allWeights = dataContainer.querySelectorAll('.multi-select-weight');
    const selectedData = Array.from(allInputs).map(input => input.value);
    const weights = Array.from(allWeights).map(input => parseFloat(input.value));

    //const selectedData = document.getElementById('multi-selectedData').value;
    const targetDateStart = document.getElementById('multi-targetDateStart').value;
    const targetDateEnd = document.getElementById('multi-targetDateEnd').value;
    const compareDateStart = document.getElementById('multi-compareDateStart').value;
    const compareDateEnd = document.getElementById('multi-compareDateEnd').value;
    const nSteps = document.getElementById('multi-nSteps').value;
    const nGraphs = document.getElementById('multi-nGraphs').value;

    console.log("Sending data with selectedData array and weights:", selectedData, weights);

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }
    console.log("Sending data:", { selectedData, targetDateStart, targetDateEnd, nSteps, nGraphs,weights });

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
            n_steps: parseInt(nSteps, 10),
            weights : weights
            //n_graphs: parseInt(nGraphs, 10)
        }),
    })
    .then(response => response.json())
    .then(data => {
        const originalChartData = JSON.parse(data.chart_data.original).data;
        const alignedChartData = JSON.parse(data.chart_data.aligned).data;
        document.getElementById('loading_bar_similarity').style.display = 'none';    
        // 차트 생성 함수 호출
        generateMultiHighCharts(originalChartData, 'multiOriginalChartContainer');
        generateMultiHighCharts(alignedChartData, 'multiAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching multi similarity data:', error);
        document.getElementById('loading_bar_similarity').style.display = 'none'; 
    });
    
}

/*************  유사변동분석   ****************/
function generateVariationAnalysis() {
    const selectedData = document.getElementById('variation-selectedData').value;
    const targetDateStart = document.getElementById('variation-targetDateStart').value;
    const targetDateEnd = document.getElementById('variation-targetDateEnd').value;
    const compareDateStart = document.getElementById('variation-compareDateStart').value;
    const compareDateEnd = document.getElementById('variation-compareDateEnd').value;
    const nSteps = document.getElementById('variation-nSteps').value;
    const nGraphs = document.getElementById('variation-nGraphs').value;

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }

    //console.log("Sending data:", JSON.stringify(payload));

    document.getElementById('loading_bar_similarity').style.display = 'block';                                
    fetch('/similarity/variation-variate-analyze/', {
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
    .then(response => response.json().then(data => {
        if (!response.ok) {
            // 에러 메시지가 포함된 응답 처리
            throw new Error(data.detail || "An error occurred");
        }
        return data;  // 성공 응답 데이터 반환
    }))
    .then(data => {
        console.log(data.chart_data.original);
        const originalChartData = data.chart_data.original;
        const alignedChartData = data.chart_data.aligned;
        document.getElementById('loading_bar_similarity').style.display = 'none';    
        // Invoke the chart creation functions
        generateVariationHighCharts(originalChartData, 'variationOriginalChartContainer');
        generateVariationHighCharts(alignedChartData, 'variationAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching similarity data:', error.message);
        alert(error.message);  // 서버 에러 메시지 또는 기본 에러 메시지를 alert로 표시
        document.getElementById('loading_bar_similarity').style.display = 'none'; 
    });
}

function formatDateWithoutTime(dateTimeStr) {
    return dateTimeStr.split(' ')[0]; 
}
function generateVariationHighCharts(chartData, containerId) {
    let container = document.getElementById(containerId);
    if (!container) {
        console.error('Container not found:', containerId);
        return;
    }
    let chartTitle = '';
    if (containerId === 'variationOriginalChartContainer') {
        chartTitle = 'Original Comparison';
    } else if (containerId === 'variationAlignedChartContainer') {
        chartTitle = 'Aligned Comparison';
    }
    const nStepsValue = parseInt(document.getElementById('nVariationStepValue').textContent, 10);
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
        console.log("**************");
        console.log(targetSeriesData.length);
        console.log("**************");
        plotLinePosition = targetSeriesData.length - 1 - nStepsValue; // Calculate position from end with nSteps back
        if (plotLinePosition >= targetSeriesData.length) {
            plotLinePosition = targetSeriesData.length - 1; // Ensure plot line is within the chart
        }
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
            }],
            max: chartData.series[0] ? chartData.series[0].data.length - 1 : null // x축의 최대값 설정
    },
    yAxis: {
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