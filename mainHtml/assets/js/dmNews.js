//******************************** 2nd GNB:: 국내 뉴스 Showing 영역 Starts *************************************//
// NAVER 뉴스 기본 정보 스크래핑해오기
function naverScrapingNews(newsType) {
    let url;
    var inputBox = document.querySelector('.naver-api-input');
    if (inputBox) {  //'내가검색하기' 쪽 인풋박스 일단 클리어 
        inputBox.value = '';  
    }
    document.querySelector('.news-api-btn').classList.remove('selected');
    switch (newsType) {
        case 1:
            url = "https://finance.naver.com/news/mainnews.naver";
            break;
        case 2:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258&section_id3=401";
            break;
        case 3:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258&section_id3=402";
            break;            
        case 4:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258&section_id3=404";
            break;                        
        case 5:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258&section_id3=406";
            break;            
        case 6:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258&section_id3=429";
            break;            
        default:
            console.error('Invalid news type');
            return;
    }
    const apiUrl = `/naver-scraping-news?url=${encodeURIComponent(url)}`;
    fetch(apiUrl)
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        const newsShowArea = document.getElementById('news_show_area');
        newsShowArea.innerHTML = '';
        data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'naver-news-item';
            div.innerHTML = `
                <img src="${item.thumb_url ? item.thumb_url : '/static/assets/images/defaultNews.jpg'}" alt="" class="naver-news-thumb">
                <div class="naver-news-content">
                    <div class="naver-news-title">${item.article_subject}</div>
                    <div class="naver-news-summary">${item.summary}</div>
                    <div class="naver-news-info">${item.press} | ${item.wdate}</div>
                </div>
            `;
            const button = document.createElement('button');
            button.className = 'naver-news-detail-btn';
            button.textContent = '자세히 보기';
            button.addEventListener('click', function(event) {
                fetchDetaildNews(item.article_link, event);
            });
            div.appendChild(button);
            newsShowArea.appendChild(div);
        });
    })
    .catch(error => {
        console.error('Error fetching news:', error);
        document.getElementById('news_show_area').innerHTML = '<p>뉴스를 가져오는 중 오류가 발생했습니다.</p>';
    });
}
// NAVER 뉴스 상세 컨텐츠 스크래핑 해오기
function fetchDetaildNews(url, event) {
    const button = event.target;
    const newsItem = button.closest('.naver-news-item');
    let detailedDiv = newsItem.nextElementSibling;

    // 자세히보기 버튼 Toggle 시키기. 
    if (detailedDiv && detailedDiv.classList.contains('naver-news-detailed')) {
        if (detailedDiv.style.display === 'none') {
            detailedDiv.style.display = 'block';
            button.textContent = '상세내용 닫기'; 
        } else {
            detailedDiv.style.display = 'none'; 
            button.textContent = '자세히 보기'; 
        }
    } else {
        fetch('/api/news-detail', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        })
        .then(response => response.text())
        .then(html => {
            const detailedNewsDiv = document.createElement('div');
            detailedNewsDiv.className = 'naver-news-detailed';
            detailedNewsDiv.innerHTML = html;
            newsItem.insertAdjacentElement('afterend', detailedNewsDiv);
            button.textContent = '상세내용 닫기'; 
        })
        .catch(error => {
            console.error('Error fetching detailed news:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'naver-news-detailed';
            errorDiv.innerHTML = '<p>자세한 뉴스를 가져오는 중 오류가 발생했습니다.</p>';
            newsItem.insertAdjacentElement('afterend', errorDiv);
            button.textContent = '상세내용 닫기'; 
        });
    }
}

// 네이버 키워드 입력란 보이게 하는 함수
function naverKeyword() {
    // 'naver-api-search-area' 요소가 이미 있는지 확인
    let searchArea = document.getElementById('naver-api-search-area');
    
    // 요소가 존재하지 않는 경우에만 생성 및 추가
    if (!searchArea) {
        searchArea = document.createElement('div');
        searchArea.setAttribute('id', 'naver-api-search-area');
        searchArea.innerHTML = `
        <span>검색할 뉴스 키워드를 입력해주세요 :</span>
        <input type="text" class="naver-api-input" placeholder="키워드 입력(예: 삼성전자)..." onfocus="this.value=''">
        <button class="naver-api-search-btn" onclick="naverSearchAPI()">검색</button>`;
        
        const newsSelectionArea = document.getElementById('news_selection_area');
        // 'news_selection_area'의 바로 다음에 검색 영역을 삽입
        document.getElementById('menu_2nd_a').insertBefore(searchArea, newsSelectionArea.nextSibling);
    }

    // naver-api-input에 자동으로 focus 설정 및 엔터키 이벤트 핸들러 설정
    const input = document.querySelector('.naver-api-input');
    if (input) {
        input.focus();
        input.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                naverSearchAPI();
            }
        });
    }
}
// 네이버 검색 API를 활용해서 뉴스까지 가져오자 
async function naverSearchAPI() {
    // 일단 다른 뉴스 버튼들 (news-btn)의 'selected' 클래스 제거
    document.querySelectorAll('.news-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    // news-api-btn에 'selected' 클래스 추가
    document.querySelector('.news-api-btn').classList.add('selected');  

    const keywordInput = document.querySelector('.naver-api-input');
    if (!keywordInput) return; 
    const keyword = keywordInput.value;
    const apiUrl = `/api/search-naver?keyword=${encodeURIComponent(keyword)}`;
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Network response was not ok');
        const { items } = await response.json(); // Destructure to get the items array

        const newsShowArea = document.getElementById('news_show_area');
        newsShowArea.innerHTML = ''; 

        items.forEach(item => {
            const title = item.title.replace(/<\/?[^>]+(>|$)/g, "");
            const description = item.description.replace(/<\/?[^>]+(>|$)/g, "");

            const div = document.createElement('div');
            div.className = 'naver-news-item';
            div.innerHTML = `
                <div class="naver-news-content">
                    <div class="naver-news-title">${title}</div>
                    <div class="naver-news-summary">${description}</div>
                    <div class="naver-news-info">${item.bloggername} | ${new Date(item.postdate).toLocaleDateString()}</div>
                </div>
                <a href="${item.link}" target="_blank" class="naver-news-detail-btn">자세히 보기</a>
            `;
            newsShowArea.appendChild(div);
        });
    } catch (error) {
        console.error('Error fetching news:', error);
        document.getElementById('news_show_area').innerHTML = '<p>뉴스를 가져오는 중 오류가 발생했습니다.</p>';
    }
}
//네이버 뉴스 GPT(AI) 의견보기 함수 ::  요약보여주기
function displaySummary(summary) {
    // 데이터 가공
    summary = summary.replace(/\*\*(.*?)\*\*/g, '<br/><br/><span style="color: #ff1480; text-transform: uppercase;">$1</span><br/>');
    summary = summary.replace(/(?:^|\s)\*(.*?)(?=\s|$)/g, '<br>*$1');
    const summaryContainer = document.querySelector('.ai-summary-result');
    summaryContainer.innerHTML = `<div class="summary-content">${summary}</div>`;
    summaryContainer.style.display = 'block';
}
//네이버 뉴스 GPT(AI) 의견보기 함수 ::  파이썬 호출 
async function naverGptAsk() {
    const newsSummaryElements = document.querySelectorAll('.naver-news-summary');
    let send_news = Array.from(newsSummaryElements).map(elem => elem.textContent.trim()).join('\n');
    if (!send_news) {
        alert('분석할 뉴스 데이터가 없습니다.');
        return;
    }
    document.getElementById('loading_bar_navergpt').style.display = 'block';  
//console.log(send_news);
    try {
        const response = await fetch('/gptRequest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: "navergpt",
                g_news: send_news
            }),
        });
        if (!response.ok) {
            document.getElementById('loading_bar_navergpt').style.display = 'none';             
            throw new Error('서버 오류가 발생했습니다.');
        }
        const data = await response.json();
        if (data.result.error) {
            document.getElementById('loading_bar_navergpt').style.display = 'none';              
            throw new Error(data.result.error);
        } else {
            document.getElementById('loading_bar_navergpt').style.display = 'none';  
            displaySummary(data.result); 
        }
    } catch (error) {
        console.error('요약 데이터를 가져오는 중 오류가 발생했습니다:', error);
        document.getElementById('loading_bar_navergpt').style.display = 'none';  
        alert('데이터를 가져오는 중 오류가 발생했습니다. 오류 메시지: ' + error.message);
    }
}

async function naverGptAskStream() {
    let fullSumMessage  = "";
    const newsSummaryElements = document.querySelectorAll('.naver-news-summary');
    let send_news = Array.from(newsSummaryElements).map(elem => elem.textContent.trim()).join('\n');
    if (!send_news) {
        alert('분석할 뉴스 데이터가 없습니다.');
        return;
    }
    document.getElementById('loading_bar_navergpt').style.display = 'block';     
    const summaryContainer = document.querySelector('.ai-summary-result');
    summaryContainer.style.display = 'block';   
    $(".ai-summary-result").html('<div class="summary-content"></div>');   
    try {
        const response = await fetch('/gptRequestStream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: "navergpt",
                g_news: send_news
            }),
        });
        if (!response.ok) {
            document.getElementById('loading_bar_navergpt').style.display = 'none';             
            throw new Error('서버 오류가 발생했습니다.');
        }
        document.getElementById('loading_bar_navergpt').style.display = 'none';             
        const reader = response.body?.pipeThrough(new TextDecoderStream()).getReader();
        while (true) {
            const res = await reader?.read();           
            if (res?.done) {
                //console.log("fullSumMessage:" + fullSumMessage)    
                fullSumMessage = fullSumMessage.replace(/\*\*(.*?)\*\*/g, '<br/><br/><span style="color: #ff1480; text-transform: uppercase;">$1</span><br/>');
                fullSumMessage = fullSumMessage.replace(/(?:^|\s)\*(.*?)(?=\s|$)/g, '<br>*$1');
                $(".summary-content").html(fullSumMessage);                  
                break;
            }
            let resValue = res?.value
            //console.log("res:" + resValue)    
            fullSumMessage   = fullSumMessage + resValue
            $(".summary-content").append(resValue)
        }        
    } catch (error) {
        console.error('요약 데이터를 가져오는 중 오류가 발생했습니다:', error);
        document.getElementById('loading_bar_navergpt').style.display = 'none';  
        alert('데이터를 가져오는 중 오류가 발생했습니다. 오류 메시지: ' + error.message);
    }
}

async function naverLamaAsk() {
    const newsSummaryElements = document.querySelectorAll('.naver-news-summary');
    let send_news = Array.from(newsSummaryElements).map(elem => elem.textContent.trim()).join('\n');
    if (!send_news) {
        alert('분석할 뉴스 데이터가 없습니다.');
        return;
    }
    document.getElementById('loading_bar_navergpt').style.display = 'block';  
//console.log(send_news);
    try {
        const response = await fetch('/groqLamaTest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: "navergpt",
                g_news: send_news
            }),
        });
        if (!response.ok) {
            document.getElementById('loading_bar_navergpt').style.display = 'none';  
            throw new Error('서버 오류가 발생했습니다.');
        }
        const data = await response.json();
        if (data.result.error) {
            document.getElementById('loading_bar_navergpt').style.display = 'none';  
            throw new Error(data.result.error);            
        } else {
            document.getElementById('loading_bar_navergpt').style.display = 'none';  
            displaySummary(data.result); 
        }
    } catch (error) {
        console.error('요약 데이터를 가져오는 중 오류가 발생했습니다:', error);
        document.getElementById('loading_bar_navergpt').style.display = 'none';  
        alert('데이터를 가져오는 중 오류가 발생했습니다. 오류 메시지: ' + error.message);
    }
}


//******************************** 2nd GNB:: 국내 뉴스 Showing 영역 Ends *************************************//