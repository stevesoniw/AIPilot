//****************************** [1ST GNB][6TH MENU]유사국면-채권 함수 Starts *******************************//  
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
    
    //console.log("***************");
    //console.log(chartDataArray);
    //console.log("***************");

    const nStepsValue = parseInt(document.getElementById('nMultiStepValue').textContent, 10);
    

    // Collect all series and format names if needed
    const allSeries = chartDataArray.series.map(series => {
        if (series.name.startsWith('Graph')) {
            const nameParts = series.name.split(': ');
            const dateRangeParts = nameParts[1].split(' to ');
            const formattedStart = formatDateWithoutTime(dateRangeParts[0]);
            const formattedEnd = formatDateWithoutTime(dateRangeParts[1]);
            return {
                name: `${nameParts[0]}: ${formattedStart} to ${formattedEnd}`,
                data: series.data
            };
        }
        return {
            name: series.name,
            data: series.data
        };
    });

    // Assuming the first dataset contains xAxis categories and is representative
    
    const categories = chartDataArray.xAxis.categories;
    let plotLinePosition = Math.max(0, categories.length - 1 - nStepsValue);

    Highcharts.chart(containerId, {
        chart: {
            type: 'line',
            zoomType: 'x'
        },
        title: {
            text: chartDataArray.title.text
        },
        xAxis: {
            categories: categories,
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
            max: categories.length - 1
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

function formatDateWithoutTime(dateTimeStr) {
    const date = new Date(dateTimeStr);
    return date.toISOString().split('T')[0]; // returns date in YYYY-MM-DD format
}
//선택한 지표 붙이기 
function appendSelectedData() {
    const selectBox = document.getElementById('multi-selectedData');
    const selectedValue = selectBox.value;
    if (selectedValue === "default") {
        return;
    }    
    const container = document.getElementById('selectedDataContainer');

    const item = document.createElement('div');
    item.className = 'multi-select-item';

    const text = document.createElement('input');
    text.type = 'text';
    text.className = 'multi-select-text';
    text.value = selectedValue;
    text.readOnly = true;

    const weightLabel = document.createElement('label');
    weightLabel.textContent = 'Weights: ';
    weightLabel.className = 'multi-select-label';

    const weightInput = document.createElement('input');
    weightInput.type = 'number';
    weightInput.className = 'multi-select-weight';
    weightInput.value = calculateWeight();
    weightInput.min = "0";
    weightInput.max = "1";
    weightInput.step = "0.1";
    weightInput.addEventListener('change', validateWeights);

    const deleteBtn = document.createElement('span');
    deleteBtn.className = 'multi-select-delete';
    deleteBtn.textContent = 'x';
    deleteBtn.onclick = function() {
        container.removeChild(item);
        validateWeights();
    };

    item.appendChild(text);
    item.appendChild(weightLabel);
    item.appendChild(weightInput);
    item.appendChild(deleteBtn);
    container.appendChild(item);
}

function calculateWeight() {
    const weights = document.querySelectorAll('.multi-select-weight');
    const count = weights.length + 1; // Including the new input
    const normalizedWeight = Math.floor(10 / count) / 10;
    let lastWeight = 1 - normalizedWeight * (count - 1);
    lastWeight = Math.round(lastWeight * 10) / 10; // Round to one decimal

    weights.forEach(input => input.value = normalizedWeight);
    return lastWeight; // Adjusted for rounding
}

function validateWeights() {
    const weights = document.querySelectorAll('.multi-select-weight');
    const sum = Array.from(weights).reduce((acc, input) => acc + parseFloat(input.value), 0);
    if (sum !== 1) {
        alert("Weights(지표별 비중)의 합은 1이 되어야 정확한 결과가 나옵니다. 참고해서 입력해주세요.");
    }
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

    if (selectedData.length === 0) {
        alert("분석할 지표를 먼저 선택해주세요!");
        return;
    }

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }
    //console.log("Sending data:", { selectedData, targetDateStart, targetDateEnd, nSteps, nGraphs,weights });
    document.getElementById('loading_bar_multi').style.display = 'block';                                
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
        /*
        console.log("aaa");
        console.log(data.chart_data.original);
        console.log("aaa");
        const originalChartData = JSON.parse(data.chart_data.original);
        const alignedChartData = JSON.parse(data.chart_data.aligned);
        document.getElementById('loading_bar_similarity').style.display = 'none';    
        // 차트 생성 함수 호출
        generateMultiHighCharts(originalChartData, 'multiOriginalChartContainer');
        generateMultiHighCharts(alignedChartData, 'multiAlignedChartContainer');*/
        document.getElementById('loading_bar_multi').style.display = 'none';    
        createAndPopulateChartContainers(data.chart_data);
        
    })
    .catch(error => {
        console.error('Error fetching multi similarity data:', error);
        document.getElementById('loading_bar_multi').style.display = 'none'; 
    });
}

function createAndPopulateChartContainers(chartData) {
    // Parsing the JSON strings in 'original' and 'aligned' properties
    if (typeof chartData.original === 'string') {
        try {
            chartData.original = JSON.parse(chartData.original);
        } catch (error) {
            console.error('Error parsing chartData.original:', error);
            return;
        }
    }
    if (typeof chartData.aligned === 'string') {
        try {
            chartData.aligned = JSON.parse(chartData.aligned);
        } catch (error) {
            console.error('Error parsing chartData.aligned:', error);
            return;
        }
    }

    const chartContainerBase = document.getElementById('chartContainerBase');
    chartContainerBase.innerHTML = ''; // Clear previous contents

    // Assuming there's a need to display both 'original' and 'aligned' charts
    // Create containers and charts for 'original'
    chartData.original.forEach((data, index) => {
        const containerId = `originalChartContainer${index}`;
        createChartContainer(chartContainerBase, data, containerId);
    });

    // Create containers and charts for 'aligned'
    chartData.aligned.forEach((data, index) => {
        const containerId = `alignedChartContainer${index}`;
        createChartContainer(chartContainerBase, data, containerId);
    });
}

function createChartContainer(base, data, containerId) {
    const div = document.createElement('div');
    div.id = containerId;
    div.className = 'chart-container';
    base.appendChild(div);

    generateMultiHighCharts(data, containerId);
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

    document.getElementById('loading_bar_variation').style.display = 'block';                                
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
        //console.log(data.chart_data.original);
        const originalChartData = data.chart_data.original;
        const alignedChartData = data.chart_data.aligned;
        document.getElementById('loading_bar_variation').style.display = 'none';    
        // Invoke the chart creation functions
        generateVariationHighCharts(originalChartData, 'variationOriginalChartContainer');
        generateVariationHighCharts(alignedChartData, 'variationAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching similarity data:', error.message);
        alert(error.message);  // 서버 에러 메시지 또는 기본 에러 메시지를 alert로 표시
        document.getElementById('loading_bar_variation').style.display = 'none'; 
    });
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
        //console.log("**************");
        //console.log(targetSeriesData.length);
        //console.log("**************");
        plotLinePosition = targetSeriesData.length - 1 - nStepsValue; 
        if (plotLinePosition >= targetSeriesData.length) {
            plotLinePosition = targetSeriesData.length - 1; 
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


//********************************* [1ST GNB][6TH MENU]유사국면-채권 함수 Ends ***************************************//   