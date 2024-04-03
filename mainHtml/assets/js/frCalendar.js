//****************************** [1ST GNB][5TH MENU]증시캘린더 함수 Starts *****************************//
async function goCalendar(calendarFile = '/batch/calendar/eco_calendar_eng.json') {
    document.getElementById('loading_bar_calendar').style.display = 'block';

    try {
        // 'batch/calendars/eco_calendar_eng.json' 파일에서 데이터를 불러옴
        const response = await fetch(calendarFile);
        if (!response.ok) {
            throw new Error('Calendar data could not be loaded.');
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
    if (btn.innerText.includes('한글번역')) {
        goCalendar('/batch/calendar/eco_calendar_kor.json');
        btn.innerText = 'Economic 영문번역';
    } else {
        goCalendar('/batch/calendar/eco_calendar_eng.json');
        btn.innerText = 'Economic 한글번역';
    }
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