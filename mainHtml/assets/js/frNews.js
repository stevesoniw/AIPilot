//************************************** 뉴스요청 함수 Starts ******************************************//
var g_news;
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

        g_news = await response.json();
        //g_news = newsResult
        const seekingNewsData = g_news;

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
            addTranslationButton(newsItem, item.title, item.content, 'lama', '한국어 번역하기(Lama)');
            addTranslationButton(newsItem, item.title, item.content, 'gpt', '한국어 번역하기(GPT)');
       

            newsContainer.appendChild(newsItem);
        });
    } else {
        console.error('Received data is not an array:', seekingNewsData);
    }
}

function addTranslationButton(newsItem, title, content, method, buttonText) {
    const translateButton = document.createElement('button');
    translateButton.className = 'newstrans-button';
    translateButton.textContent = buttonText;
    newsItem.querySelector('.news-content > div').appendChild(translateButton);

    translateButton.addEventListener('click', async function() {
        const loadingBar = document.createElement('div');
        loadingBar.className = 'loading-bar';
        loadingBar.innerHTML = '<img src="/static/assets/images/LoadingBar_C.gif" alt="Loading" />';
        newsItem.appendChild(loadingBar);

        try {
            const response = await fetch('/frnews-translate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title, content, method })
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
}

async function gptRequest(action, llm) {
    if (g_news.length === 0) {
        alert("뉴스데이터가 조회된 후 클릭해주세요");
        return;
    }
    document.getElementById('gpt_opinion').innerHTML = ""; 
    document.getElementById('gpt_summary').innerHTML = "";  
    document.getElementById('gpt-thoughts-container').style.display = 'none'; 
    document.getElementById('gpt-summary-container').style.display = 'none'; 

    //alert(JSON.stringify({action: action, g_news: g_news}));
    const sanitizedNews = g_news.map(newsItem => ({
        title: newsItem.title,  
        content: newsItem.content 
    }));    
    console.log("**************************");
    console.log(g_news);
    console.log("**************************");    
    console.log(sanitizedNews);

    const requestOptions = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({action: action, g_news: sanitizedNews, llm : llm})                
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
        document.getElementById('loading_bar_gpt').style.display = 'none';  
        console.error('Error:', error);
    }
}

//************************************** 뉴스요청 함수 Ends ******************************************//        