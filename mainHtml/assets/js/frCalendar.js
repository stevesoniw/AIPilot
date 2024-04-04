//****************************** [1ST GNB][5TH MENU]증시캘린더 함수 Starts *****************************//
async function goCalendar(calendarFile = '/batch/calendar/eco_calendar_eng.json') {
    document.getElementById('loading_bar_calendar').style.display = 'block';

    try {
        // 'batch/calendars/eco_calendar_eng.json' 파일에서 데이터를 불러옴
        const response = await fetch(calendarFile);
        if (!response.ok) {
            throw new Error('Economic Calendar data could not be loaded.');
        }
        const calendarData = await response.json();
        console.log(calendarData);

        // "start" 날짜가 "2024-01-01" 이후인 데이터만 필터링
        //const filteredData = calendarData.filter(event => new Date(event.start) >= new Date("2024-01-01"));

        var calendarEl = document.getElementById('calendar');
        if (!calendarEl) {
            alert('Calendar element not found on the page.');
            return;
        }
        var calendar = new FullCalendar.Calendar(calendarEl, {
            eventLimit: true,
            initialView: 'dayGridMonth',
            headerToolbar: { left: 'prev,next today', center: 'title',  right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'},
            timeZone: 'UTC',
            expandRows: true,
            locale: "KO",
            firstDay: 1,
            navLinks: true,
            handleWindowResize: true,
            windowResizeDelay: 100,
            nowIndicator: true,
            dayMaxEvents: true, // 이벤트가 오버되면 높이 제한 (+ 몇 개식으로 표현)
            events: calendarData.map(event => ({
                id: event.id?.toString() || 'default-id',
                title: event.title,
                start: event.start,
                end: event.end,
                color: `#${event.hexColor}`, // 색상 설정
                description: event.shortDesc // 설명 추가
            })),
            eventContent: function(arg) { // 이벤트 내용 커스터마이징
                var element = document.createElement('div');
                element.innerHTML = `<b>${arg.event.title}</b><br>${arg.event.extendedProps.description}`;
                return { domNodes: [element] };
            },
            // 날짜 클릭 이벤트 처리기 추가
            dateClick: function(info) {
                console.log("Selected date:", info.dateStr);

                // 해당 날짜에 예정된 모든 이벤트의 title 출력
                let events = calendar.getEvents().filter(event => {
                    // 이벤트 시작과 종료 날짜를 "YYYY-MM-DD" 포맷으로 변환
                    let eventStartDate = event.startStr.split("T")[0];
                    let eventEndDate = event.endStr ? event.endStr.split("T")[0] : eventStartDate;
                    return info.dateStr >= eventStartDate && info.dateStr <= eventEndDate;
                }).map(event => event.title);
            
                console.log("Events on this day:", events);
                selectData = info.dateStr;
                title = events.join(", ");
                calendarEventPopup(selectData, title);
                //alert(`Selected date: ${info.dateStr}\nEvents: ${events.join(", ")}`);
            }            
        });
        calendar.render();
        //txt 파일을 읽어서 calendar_ai_box에 AI 요약내용 채워넣는 코드 추가
        const responseSummary = await fetch('/batch/calendar/eco_calendar_aisummary.html');
        if (!responseSummary.ok) {
            throw new Error('AI summary could not be loaded.');
        }
        const summaryText = await responseSummary.text();
        document.getElementById('calendar_ai_box').innerHTML = summaryText; 

    } catch (error) {
        console.error('Error loading calendar data:', error);
        alert('Error loading calendar data.');
    } finally {
        document.getElementById('loading_bar_calendar').style.display = 'none';
    }
}

function translateCalendar() {
    const btn = document.getElementById('transCalOpt');
    if (btn.innerText.includes('한글')) {
        goCalendar('/batch/calendar/eco_calendar_kor.json');
        btn.innerText = 'Economic Calendar(영문)';
    } else {
        goCalendar('/batch/calendar/eco_calendar_eng.json');
        btn.innerText = 'Economic Calendar(한글)';
    }
}
//****************************** [1ST GNB][5TH MENU]증시캘린더 함수 Ends *****************************//                
//****************************** [1ST GNB][6TH MENU]IPO캘린더 함수 Starts *****************************//                
async function ipoCalendar() {
    document.getElementById('loading_bar_calendar').style.display = 'block';
    let ipoCalendarData;
    try {
        /**
        const response = await fetch('/calendar/ipo', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        ipoCalendarData = await response.json(); **/
        const response = await fetch('/batch/calendar/ipo_calendar_eng.json');
        if (!response.ok) {
            throw new Error('IPO Calendar data could not be loaded.');
        }
        ipoCalendarData = await response.json();
        console.log(ipoCalendarData);

    } catch (error) {
        console.error("Failed to fetch IPO calendar data:", error);
        document.getElementById('loading_bar_calendar').style.display = 'none';
        alert('Failed to load IPO Calendar data. Please try again later.');
        return;
    } finally {
        document.getElementById('loading_bar_calendar').style.display = 'none';
    }

    // Check if the ipoCalendarData or ipoCalendarData.ipoCalendar is undefined or null
    if (!ipoCalendarData || !ipoCalendarData.ipoCalendar) {
        alert('No IPO Calendar data available.');
        return;
    }

    const defaultText = '[N/A]';
    const colors = ['#5b24da', '#9819ad', '#0c9d12'];
    const ipoEvents = ipoCalendarData.ipoCalendar.map(event => {
        const color = colors[Math.floor(Math.random() * colors.length)];

        return {
            id: event.symbol || defaultText,
            title: `${event.name || defaultText} (${event.symbol || defaultText})${event.numberOfShares && event.numberOfShares > 1 ? ' +' : ''}`,
            start: event.date || new Date().toISOString().slice(0, 10), // Use current date as fallback
            color: color,
            description: `
                Exchange: ${event.exchange || defaultText}<br>
                Shares: ${event.numberOfShares || defaultText}<br>
                Price: ${event.price || defaultText}<br>
                Status: ${event.status || defaultText}<br>
                Total Shares Value: ${event.totalSharesValue ? `$${event.totalSharesValue.toLocaleString()}` : defaultText}
            `
        };
    });

    var calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        console.error('Calendar element not found on the page.');
        return;
    }
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        timeZone: 'UTC',
        expandRows: true,
        locale: "KO",
        firstDay: 1,
        navLinks: true,
        handleWindowResize: true,
        windowResizeDelay: 100,
        nowIndicator: true,
        dayMaxEvents: true,
        eventLimit: true,
        events: ipoEvents,
        eventContent: function(arg) {
            var element = document.createElement('div');
            element.innerHTML = `<b>${arg.event.title}</b><br>${arg.event.extendedProps.description}`;
            return { domNodes: [element] };
        }
    });
    calendar.render();
}

//특정 날짜 클릭시 레이어 팝업으로 해당 일의 events를 보여주는 레이어팝업을 호출한다.
function calendarEventPopup(date, titles) {
    if (!titles) {
        // titles 데이터가 없으면 함수 실행 중지
        return;
    }

    let titleStr = titles.split(", "); // titlesStr를 배열로 변환

    // titles 데이터가 없거나 빈 문자열인 경우 함수 실행 중지
    if (titleStr.length === 0 || (titleStr.length === 1 && titleStr[0] === '')) {
        return;
    }

    let popupHTML = `<div id="fancyCalendarPopup" class="fancy-calendar-popup">
      <span>검색할 이벤트를 선택해주세요.</span>
      <h2>${date} 스케쥴</h2>
      <form id="eventForm" class="fancy-calendar-form">`;

    titleStr.forEach((title, index) => {
        const titleValue = title.split(' ').slice(2).join(' ');
        // title 데이터가 단 하나인 경우 또는 첫 번째 항목에 대해 라디오 버튼 자동 선택
        const checkedAttribute = titleStr.length === 1 || index === 0 ? 'checked' : '';
        popupHTML += `<label><input type="radio" name="eventTitle" value="${titleValue}" ${checkedAttribute}>${title}</label><br>`;
    });

    popupHTML += `</form>
      <div class="calendar-button-group">
        <button type="button" class="calendar-opt-btn" onclick="searchEvents()">Search</button>
        <button type="button" class="calendar-opt-btn" onclick="closeCalPopup()">Close</button>
      </div>
    </div>`;

    const container = document.getElementById('popupEventCon');
    if (container !== null) {
        container.classList.remove('popupHidden');
        container.innerHTML = popupHTML;
    } else {
        console.error('popupEventCon container not found');
    }
}

function closeCalPopup() {
    const container = document.getElementById('popupEventCon');
    if (container) {
      container.classList.add('popupHidden'); // 팝업 숨김
    }
  }

async function searchEvents() {
    response = await fetch('/batch/calendar/eco_calendar_eng.json');
    if (!response.ok) {
        throw new Error('fetching Calendar data for Search failed when loading the data.');
    }
    const ecoCalendarData = await response.json();
    const selectedTitle = document.querySelector('input[name="eventTitle"]:checked').value;
//  console.log(selectedTitle);
    const matchingEvents = ecoCalendarData.filter(event => event.title.includes(selectedTitle)).map(event => {
      return { title: event.title.split(' ').slice(2).join(' '), date: new Date(event.start).toLocaleString() };
    });
    displayEvents(matchingEvents);
    closeCalPopup();
}
  
function displayEvents(events) {
    const detailsDiv = document.getElementById('fancyCalendarDetails');
    detailsDiv.innerHTML = '';

    const titleText = document.createElement('div');
    titleText.className = 'calendar-search-title';
    titleText.textContent = '■ 과거 동일한 발표 전후의 주가데이터 보기';
    detailsDiv.appendChild(titleText);

    const selectContainer = document.createElement('div');
    selectContainer.className = 'calendar-search-select-container';
    detailsDiv.appendChild(selectContainer);

    const selectBox = document.createElement('select');
    selectBox.className = 'calendar-search-select';
    events.forEach(event => {
        const option = document.createElement('option');
        option.value = event.date;
        option.textContent = `${event.date} || ${event.title}`;
        selectBox.appendChild(option);
    });
    selectContainer.appendChild(selectBox);

    const fromLabel = document.createElement('label');
    fromLabel.className = 'calLabel';
    fromLabel.setAttribute('for', 'fromCalChartDate');
    fromLabel.textContent = 'From';
    selectContainer.appendChild(fromLabel);

    const fromInput = document.createElement('input');
    fromInput.className = 'calInput';
    fromInput.setAttribute('type', 'text');
    fromInput.id = 'fromCalChartDate';
    fromInput.name = 'fromCalChartDate';
    selectContainer.appendChild(fromInput);

    const toLabel = document.createElement('label');
    toLabel.className = 'calLabel';
    toLabel.setAttribute('for', 'toCalChartDate');
    toLabel.textContent = 'To';
    selectContainer.appendChild(toLabel);

    const toInput = document.createElement('input');
    toInput.className = 'calInput';
    toInput.setAttribute('type', 'text');
    toInput.id = 'toCalChartDate';
    toInput.name = 'toCalChartDate';
    selectContainer.appendChild(toInput);

    $("#fromCalChartDate, #toCalChartDate").datepicker({
        dateFormat: "yy-mm-dd",
        changeMonth: true,
        changeYear: true
    });    

    const searchButton = document.createElement('button');
    searchButton.className = 'calendar-search-btn';
    searchButton.textContent = '검색';
    selectContainer.appendChild(searchButton);

    // Select box 변경 이벤트 리스너 추가
    selectBox.addEventListener('change', function() {
        const selectedDate = this.value.split(' || ')[0]; // 날짜만 추출
        const dateParts = selectedDate.split('.').map(part => part.trim());
        if (dateParts.length > 2) {
            const year = dateParts[0];
            const month = dateParts[1].padStart(2, '0');
            const day = dateParts[2].padStart(2, '0');
            const formattedDate = `${year}-${month}-${day}`;

            const userDateObj = new Date(formattedDate);
            const fromDateObj = new Date(userDateObj.getTime() - 7 * 24 * 60 * 60 * 1000); // 7일 전
            const toDateObj = new Date(userDateObj.getTime() + 7 * 24 * 60 * 60 * 1000); // 7일 후

            // 날짜를 YYYY-MM-DD 형식으로 변환
            const fromDate = fromDateObj.toISOString().split('T')[0];
            const toDate = toDateObj.toISOString().split('T')[0];

            document.getElementById('fromCalChartDate').value = fromDate;
            document.getElementById('toCalChartDate').value = toDate;
        }
    });

    searchButton.onclick = () => {
        const fromDate = document.getElementById('fromCalChartDate').value;
        const toDate = document.getElementById('toCalChartDate').value;
        fetchCalendarUSChart(fromDate, toDate);
    };
}

// 실제 차트 그리는 함수 (feat.하이차트)
async function fetchCalendarUSChart(userDate) {
    let fromDate, toDate;
    if (userDate) {
        // userDate 파라미터가 주어진 경우, 일주일 전후로 fromDate와 toDate를 설정
        const userDateObj = new Date(userDate);
        const fromDateObj = new Date(userDateObj.getTime() - 7 * 24 * 60 * 60 * 1000); // 7일 전
        const toDateObj = new Date(userDateObj.getTime() + 7 * 24 * 60 * 60 * 1000); // 7일 후

        // 날짜를 YYYY-MM-DD 형식으로 변환
        fromDate = fromDateObj.toISOString().split('T')[0];
        toDate = toDateObj.toISOString().split('T')[0];

        document.getElementById('fromCalChartDate').value = fromDate;
        document.getElementById('toCalChartDate').value = toDate;
    } else {
        // userDate 파라미터가 없는 경우, input 필드에서 날짜를 읽음
        fromDate = document.getElementById('fromCalChartDate').value;
        toDate = document.getElementById('toCalChartDate').value;
        if (!fromDate || !toDate) {
            alert('검색하실 날짜를 선택해주세요.');
            return;
        }
    }
    document.getElementById('calendarChartContainer').innerHTML = ''; 
    const requestBody = JSON.stringify({ fromDate, toDate });
    document.getElementById('loading_bar_calchart').style.display = 'block';
    try {
        const response = await fetch('/calendar-us-chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: requestBody
        });
        if (!response.ok) throw new Error('Network response was not ok.');
        const responseData = await response.json();
        document.getElementById('loading_bar_calchart').style.display = 'none';
        console.log("***************************");
        console.log(responseData.chartData);
        drawCalendarChart(responseData.chartData); // 차트그리기
    } catch (error) {
        document.getElementById('loading_bar_calchart').style.display = 'none';
        console.error('Error fetching calendar chart data:', error);
    }
}

function drawCalendarChart(chartData) {
    // 데이터 유효성 검사
    if (!chartData || !chartData.labels || chartData.labels.length === 0 || !chartData.datasets || chartData.datasets.some(dataset => dataset.data.length === 0)) {
        console.error('Invalid or missing dow chart data');
        alert('차트 데이터가 유효하지 않습니다.');
        return;
    }
    var container;
    container = document.getElementById('calendarChartContainer');    
    // 차트 컨테이너 존재 여부 검사
    if (!container) {
        console.error('Chart container not found');
        alert('차트 컨테이너를 찾을 수 없습니다.');
        return; 
    }
    const financialData = chartData.labels.map((label, index) => [
        Date.parse(label), // x 값: 타임스탬프로 변환
        chartData.datasets[0].data[index], // open
        chartData.datasets[1].data[index], // high
        chartData.datasets[2].data[index], // low
        chartData.datasets[3].data[index]  // close
    ]);
    // Highstock 사용하여 차트 생성
    Highcharts.stockChart(container, {
        chart: {
            backgroundColor: 'transparent'
        },
        rangeSelector: {
            selected: 1
        },
        title: {
            text: '다우 지수 데이터'
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
//****************************** [1ST GNB][6TH MENU]IPO캘린더 함수 Ends *******************************//   