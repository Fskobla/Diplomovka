import json

import requests
from bs4 import BeautifulSoup
from app import db
from app.models import Links, Authors, Citations, Keywords


class Sciendo:
    def __init__(self, word: str):
        self.word = word

    def get_links(self):
        links = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'sk,en-US;q=0.7,en;q=0.3',
            'Origin': 'https://sciendo.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

        page_number = 0
        while True:
            params = {
                'commonSearchText': {self.word},
                'page': str(page_number),
                'packageType': 'Article'
            }

            response = requests.get('https://intapi.sciendo.com/search/filterData', params=params, headers=headers)
            if response.status_code == 200:
                json_data = response.json()
                page_number = page_number + 1
                print(page_number)
                if len(json_data["searchHits"]) == 0:
                    break
                else:
                    for j in range(0, len(json_data['searchHits'])):
                        link = "https://sciendo.com/article/" + (json_data['searchHits'][j]['content']['doi'])
                        print(link)
                        links.append(link)

        print(len(links))
        return links

    def scrape_links(self):
        links = self.get_links()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'sk,en-US;q=0.7,en;q=0.3',
            'Origin': 'https://sciendo.com',
            'Connection': 'keep-alive',
            'Referer': 'https://sciendo.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

        for i in range(10):
            response = requests.get(links[i], headers=headers)
            print(response.encoding)

            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                try:
                    data = json.loads(
                        page.find('script', id="__NEXT_DATA__", type='application/json').text.encode('utf-8'))

                    link = response.url
                    description = data['props']['pageProps']['product']['longDescription']
                    article_title = data['props']['pageProps']['product']['articleData']['articleTitle']
                    authors = get_authors(
                        data['props']['pageProps']['product']['articleData']['contribGroup']['contrib'])
                    image = data['props']['pageProps']['product']['coverUrl']
                    date = data['props']['pageProps']['product']['articleData']['publishedDate']

                    if data['props']['pageProps']['product']['articleData']['keywords'] is not None:
                        keywords = data['props']['pageProps']['product']['articleData']['keywords']
                    else:
                        keywords = []

                    if data['props']['pageProps']['product']['articleData']['referenceList'] is not None:
                        citations = get_citations(data['props']['pageProps']['product']['articleData']['referenceList'])
                    else:
                        citations = []

                    db_citations = [Citations(reference=citation) for citation in citations]
                    db_keywords = [Keywords(word=keyword) for keyword in keywords]
                    db_authors = [Authors(name=name) for name in authors]
                    db_links = Links(link=link, word=self.word, description=description, article_title=article_title,
                                     image=image, date=date, authors=db_authors, keywords=db_keywords,
                                     citations=db_citations)
                    db.session.add(db_links)
                    db.session.commit()
                except:
                    db.session.rollback()
                finally:
                    db.session.close()


def get_authors(authors_json):
    authors = []

    for i in range(len(authors_json)):
        authors.append(authors_json[i]['name']['given-names'] + " " + authors_json[i]['name']['surname'])

    return authors


def get_citations(citations_json):
    citations = []

    for i in range(len(citations_json)):
        citations.append(citations_json[i]['citeString'])

    return citations
