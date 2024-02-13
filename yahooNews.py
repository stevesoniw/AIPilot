import requests
from bs4 import BeautifulSoup

def requests_get(url):
    try:
        return requests.get(url)
    except Exception as e:
        print(f"Exception occurred while trying to get url: {url}, error: {str(e)}")
        return None

def scrape_finance_news(keyword):
    encoded_keyword = requests.utils.quote(keyword)
    search_url = f'https://seekingalpha.com/search?q={encoded_keyword}&tab=headlines'
    response = requests_get(search_url)
    if response:
        soup = BeautifulSoup(response.content, 'html.parser')
        link_elements = soup.select('a[data-test-id="post-list-item-title"]')
        for link in link_elements:
            article_url = "https://seekingalpha.com" + link['href']
            print("Article URL:", article_url)
            # 여기에서 추가적으로 각 기사 URL에 대한 스크랩 로직을 구현할 수 있습니다.
    else:
        print("Failed to retrieve news")

if __name__ == '__main__':
    keyword = "international bonds"
    scrape_finance_news(keyword)
