//****************************** [1ST GNB][7TH MENU]유사국면-해외주식 함수 Starts *******************************//  
function generateFsSimilarityAnalysis() {
    const selectedData = document.getElementById('frst_phase_ticker').value;
    const targetDateStart = document.getElementById('frst-targetDateStart').value;
    const targetDateEnd = document.getElementById('frst-targetDateEnd').value;
    const compareDateStart = document.getElementById('frst-compareDateStart').value;
    const compareDateEnd = document.getElementById('frst-compareDateEnd').value;
    const nSteps = document.getElementById('frst-nSteps').value;
    const nGraphs = document.getElementById('frst-nGraphs').value;

    if (!targetDateStart || !targetDateEnd || !compareDateStart || !compareDateEnd) {
        alert("날짜 범위를 꼭 지정해주세요!");
        return;
    }

    //console.log("Sending data:", JSON.stringify(payload));

    document.getElementById('loading_bar_frst').style.display = 'block';                                
    fetch('/similarity/foreign-stock-analyze/', {
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
        document.getElementById('loading_bar_frst').style.display = 'none';    

        generateFrstHighCharts(originalChartData, 'frstOriginalChartContainer');
        generateFrstHighCharts(alignedChartData, 'frstAlignedChartContainer');
    })
    .catch(error => {
        console.error('Error fetching frst data:', error.message);
        alert(error.message);  // 서버 에러 메시지 또는 기본 에러 메시지를 alert로 표시
        document.getElementById('loading_bar_frst').style.display = 'none'; 
    });
}

function generateFrstHighCharts(chartData, containerId) {
    let container = document.getElementById(containerId);
    if (!container) {
        console.error('Container not found:', containerId);
        return;
    }

    if (!chartData || !chartData.series) {
        alert('해당 종목의 차트데이터가 존재하지 않습니다.');
        return;
    }    
    let chartTitle = '';
    if (containerId === 'variationOriginalChartContainer') {
        chartTitle = 'Original Comparison';
    } else if (containerId === 'variationAlignedChartContainer') {
        chartTitle = 'Aligned Comparison';
    }
    document.getElementById('frstNewsSearch').style.display = 'flex';
    const nStepsValue = parseInt(document.getElementById('nFrstStepValue').textContent, 10);
    let plotLinePosition = null;

    const formattedSeries = chartData.series.map((series, index) => {
        if (series.name.startsWith('Graph')) {
            const nameParts = series.name.split(': ');
            const dateRangeParts = nameParts[1].split(' to ');
            const formattedStart = formatDateWithoutTime(dateRangeParts[0]);
            const formattedEnd = formatDateWithoutTime(dateRangeParts[1]);
            series.name = `${nameParts[0]}: ${formattedStart} to ${formattedEnd}`;

            if (index === 1) {
                const fromDateInput = document.getElementById('frst-news-from-date');
                const toDateInput = document.getElementById('frst-news-to-date');
                if (fromDateInput && toDateInput) {
                    fromDateInput.value = formattedStart;
                    toDateInput.value = formattedEnd;
                }
            }
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
//과거 시점 뉴스 검색
async function frstPastNews() {
    try {
        document.getElementById('loading_bar_frst').style.display = 'block';
        const ticker = document.getElementById('frst_phase_ticker').value;
        const fromDate = document.getElementById('frst-news-from-date').value;
        const toDate = document.getElementById('frst-news-to-date').value;   
        const fromTimestamp = convertDateToTimestamp(fromDate);
        const toTimestamp = convertDateToTimestamp(toDate);

        const response = await fetch(`/similarity/frstPastNews/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                ticker: ticker, 
                from_date: fromTimestamp,
                to_date: toTimestamp
            }),
        });
        const news_data = await response.json();
        document.getElementById('loading_bar_frst').style.display = 'none';
        if (news_data && news_data.length > 0) {
            displayFrstNews(news_data);  // Function to process and display data
        } else {
            alert("해당 시점의 뉴스가 존재하지 않습니다.\n다시 검색해주세요.");
        }        
    } catch (error) {
        console.error('Error loading fetch frst news', error);
        document.getElementById('loading_bar_frst').style.display = 'none';
    }
}

function displayFrstNews(news_data) {
    const resultsContainer = document.getElementById('frstNewsResults');
    if (!resultsContainer) {
        console.error('frstNewsResults container not found');
        return;
    }

    resultsContainer.innerHTML = '';  // Clear previous results
    news_data.forEach(item => {
        const imageUrl = item.gettyImageUrl || `/static/assets/images/defaultNews${Math.floor(Math.random() * 25) + 1}.jpg`;
        const newsDiv = document.createElement('div');
        newsDiv.className = 'frst-flex-wrap';  // Changed class name to match the styling
        newsDiv.innerHTML = `
            <span class="frst-date-label">${new Date(item.publishOn).toLocaleDateString()}</span>
            <div class="frst-left-img-wrap">
                <img src="${imageUrl}" alt="News Image" class="frst-news-image">
            </div>
            <div class="frst-content">
                <h4 class="frst-content-tit">${item.title}</h4>
                <div class="frst-content-btn-wrap">
                    <a href="${item.link}" class="frst-content-btn blue" target="_blank">원문보기</a>`
                    // <button class="frst-content-btn orange">AI 요약하기</button>
                `</div>
            </div>
        `;
        resultsContainer.appendChild(newsDiv);
    });
}



//********************************* [1ST GNB][7TH MENU]유사국면-해외주식 함수 Ends ***************************************//   