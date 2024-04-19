//************************************** 뉴스요청 함수 Starts ******************************************//

async function goNews() {
    const checkboxes = document.querySelectorAll("#categoryForm input[name='categories']");
    const selectedCategories = Array.from(checkboxes)
                                 .filter(checkbox => checkbox.checked)
                                 .map(checkbox => checkbox.value);

    // 하나도 체크하지 않은 경우 알림을 표시하고 함수를 종료합니다.
    if (selectedCategories.length === 0) {
        alert("하나 이상의 카테고리를 선택하세요.");
        return;
    }
    document.getElementById('gpt_opinion').innerHTML = ""; 
    document.getElementById('gpt_summary').innerHTML = "";  
    document.getElementById('gpt-thoughts-container').style.display = 'none'; 
    document.getElementById('gpt-summary-container').style.display = 'none';             
    document.getElementById('loading_bar_news').style.display = 'block';    

    try {
        const newsContainer = document.getElementById('news');
        newsContainer.innerHTML = '';                
        const response = await fetch('/seekingNews', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({categories: selectedCategories})
        });

        seekingNewsData = await response.json();
        //g_news = newsResult
        //const seekingNewsData = JSON.parse(g_news);
        if (seekingNewsData) {
            // displayNews 함수를 호출하여 뉴스 데이터를 화면에 표시
            document.getElementById('loading_bar_news').style.display = 'none';
            displayNews(seekingNewsData);
        } else {
            console.error('could not get the seekingNewsData');
        }
    } catch (error) {
        console.error('Error fetching news:', error);
    } finally {
        document.getElementById('loading_bar_news').style.display = 'none';
    }  
}
// 뉴스 데이터 갖고와서 HTML로 넣어주는 함수 
function displayNews(seekingNewsData) {
    const newsContainer = document.getElementById('news');
    newsContainer.innerHTML = '';
    const defaultImageUrl = "/static/assets/images/nature.jpg";
    if (Array.isArray(seekingNewsData)) {
        seekingNewsData.forEach(item => {
            const imageUrl = item.gettyImageUrl || defaultImageUrl;
            const newsItem = document.createElement('div');
            newsItem.className = 'news-item';
            newsItem.innerHTML = `
                <div class="news-content">
                    <img src="${imageUrl}" alt="News Image">
                    <div>
                        <div class="news-title">${item.title}</div>
                        <p class="news-body">${item.content}</p>
                        <div class="publish-date">Published on: ${item.publishOn}</div>
                    </div>
                </div>
            `;
            const translateButton = document.createElement('button');
            translateButton.className = 'newstrans-button';
            translateButton.textContent = '한국어 번역하기';
            newsItem.querySelector('.news-content > div').appendChild(translateButton); // 버튼을 뉴스 컨텐츠 div에 추가

            translateButton.addEventListener('click', async function() {
                const loadingBar = document.createElement('div');
                loadingBar.className = 'loading-bar';
                loadingBar.innerHTML = '<img src="/static/assets/images/LoadingBar_C.gif" alt="Loading" />';
                newsItem.appendChild(loadingBar);

                try {
                    const response = await fetch('/translate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ title: item.title, content: item.content })
                    });
                    if (!response.ok) throw new Error('Network response was not ok.');
                    const translatedData = await response.json();

                    newsItem.querySelector('.news-title').textContent = translatedData.title;
                    newsItem.querySelector('.news-body').innerHTML = translatedData.content;
                } catch (error) {
                    console.error('Error:', error);
                } finally {
                    loadingBar.remove();
                }
            });

            newsContainer.appendChild(newsItem);
        });
    } else {
        console.error('Received data is not an array:', seekingNewsData);
    }
}
async function gptRequest(action) {
    if (g_news.length === 0) {
        alert("뉴스데이터가 조회된 후 클릭해주세요");
        return;
    }
    document.getElementById('gpt_opinion').innerHTML = ""; 
    document.getElementById('gpt_summary').innerHTML = "";  
    document.getElementById('gpt-thoughts-container').style.display = 'none'; 
    document.getElementById('gpt-summary-container').style.display = 'none'; 

    //alert(JSON.stringify({action: action, g_news: g_news}));
    const requestOptions = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({action: action, g_news: g_news})                
    };

    try {
        document.getElementById('loading_bar_gpt').style.display = 'block';                
        const response = await fetch('/gptRequest', requestOptions);
        const data = await response.json();
        console.log(data);

        if (action === 'translate') {
            document.getElementById('loading_bar_gpt').style.display = 'none';                    
            displayNews(JSON.parse(data.result)); 
        } else if (action === 'opinions') {
            const formattedText = data.result.replace(/\n/g, '<br>');
            document.getElementById('gpt_opinion').innerHTML = formattedText;                    
            document.getElementById('gpt-thoughts-container').style.display = 'block'; 
            document.getElementById('loading_bar_gpt').style.display = 'none';
        }else if (action === 'summarize') {
            const formattedText = data.result.replace(/\n/g, '<br>');                    
            document.getElementById('gpt_summary').innerHTML = formattedText; 
            document.getElementById('gpt-summary-container').style.display = 'block'; 
            document.getElementById('loading_bar_gpt').style.display = 'none';
        }

    } catch (error) {
        console.error('Error:', error);
    }
}

//************************************** 뉴스요청 함수 Ends ******************************************//        