//****************************** [1ST GNB][5TH MENU]증시캘린더 함수 Starts *****************************//
async function goCalendar() {
    document.getElementById('loading_bar_calendar').style.display = 'block';    
    const response = await fetch('/calendar', {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    });
    const calendarData = await response.json(); 
    document.getElementById('loading_bar_calendar').style.display = 'none';    

    console.log(calendarData);

    // "start" 날짜가 "2024-01-01" 이후인 데이터만 필터링
    const filteredData = calendarData.filter(event => new Date(event.start) >= new Date("2024-01-01"));

    // FullCalendar 초기화 및 데이터 표시
    var calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        // 달력 컨테이너가 아직 페이지에 없는 경우
        alert('Calendar element not found on the page.');
        return;
    }
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: { left: 'prev,next today', center: 'title',  right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'},
        timeZone: 'UTC',
        expandRows: true, 
        locale : "KO",
        firstDay: 1,
        navLinks: true, 
        ihandleWindowResize : true,
        windowResizeDelay : 100,
        nowIndicator: true,
        dayMaxEvents: true, // 이벤트가 오버되면 높이 제한 (+ 몇 개식으로 표현)
        eventLimit: true, // 더 보기 버튼 활성화              
        events: filteredData.map(event => ({
            id: event.id.toString(),
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
        }
        });
    calendar.render();
}
//****************************** [1ST GNB][5TH MENU]증시캘린더 함수 Ends *****************************//                
//****************************** [1ST GNB][6TH MENU]IPO캘린더 함수 Starts *****************************//                
async function goIpoCalendar() {
    document.getElementById('loading_bar_ipoCalendar').style.display = 'block';
    let ipoCalendarData;
    try {
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
        ipoCalendarData = await response.json();
    } catch (error) {
        console.error("Failed to fetch IPO calendar data:", error);
        document.getElementById('loading_bar_ipoCalendar').style.display = 'none';
        alert('Failed to load IPO Calendar data. Please try again later.');
        return;
    } finally {
        document.getElementById('loading_bar_ipoCalendar').style.display = 'none';
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

    var calendarEl = document.getElementById('ipo_calendar');
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

//****************************** [1ST GNB][6TH MENU]IPO캘린더 함수 Ends *******************************//   