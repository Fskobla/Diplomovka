import json
import time

import requests
from bs4 import BeautifulSoup
import psycopg2.errors
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Links, Authors, Citations, Keywords, BadLinks
from app.spiders.utils.bad_links_exception import BadLinkException
from app.spiders.utils.database_operations import remove_links_from_database, remove_bad_links_from_database


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

        for i in range(len(links)):
            response = requests.get(links[i], headers=headers)
            time.sleep(0.4)

            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                try:
                    data = json.loads(page.find('script', id="__NEXT_DATA__", type='application/json').text.encode('utf-8', 'ignore'))

                    # Link
                    try:
                        link = response.url
                    except (psycopg2.errors.UniqueViolation, UnicodeEncodeError):
                        raise BadLinkException("Link url problematic encoding")

                    # Image if exists
                    image = data['props']['pageProps']['product']['coverUrl']

                    # Published date
                    try:
                        date = data['props']['pageProps']['product']['articleData']['publishedDate']
                    except (KeyError, UnicodeEncodeError, AttributeError, TypeError):
                        raise BadLinkException("Published date is missing")

                    # Description
                    try:
                        description = data['props']['pageProps']['product']['longDescription']
                        if isinstance(description, list):
                            description = [d.encode('utf-8', 'ignore').decode('utf-8', 'ignore') for d in description]
                        else:
                            description = description.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                    except (KeyError, UnicodeEncodeError, AttributeError, TypeError):
                        raise BadLinkException("Description missing")

                    # Article_title
                    try:
                        article_title = data['props']['pageProps']['product']['articleData']['articleTitle']
                    except (KeyError, UnicodeEncodeError, AttributeError, TypeError):
                        raise BadLinkException("Article title missing")

                    # Authors
                    try:
                        authors = get_authors(
                            data['props']['pageProps']['product']['articleData']['contribGroup']['contrib'])
                    except (KeyError, UnicodeEncodeError, AttributeError, TypeError):
                        raise BadLinkException("Authors missing")

                    # Keywords
                    try:
                        keywords = data['props']['pageProps']['product']['articleData']['keywords']
                    except (KeyError, UnicodeEncodeError, AttributeError, TypeError):
                        raise BadLinkException("Keywords missing")

                    # Citations
                    try:
                        citations = get_citations(data['props']['pageProps']['product']['articleData']['referenceList'])
                    except (KeyError, UnicodeEncodeError, AttributeError, TypeError):
                        raise BadLinkException("Citations missing")

                    db_citations = [Citations(reference=citation) for citation in citations]
                    db_links = Links(link=link, word=self.word, source='Sciendo', description=description, article_title=article_title,
                                     image=image, date=date)
                    db.session.add(db_links)
                    db.session.commit()

                    db_keywords = [Keywords(word=keyword) for keyword in keywords]
                    db_authors = [Authors(name=name) for name in authors]

                    db_links.authors = db_authors
                    db_links.keywords = db_keywords
                    db_links.citations = db_citations
                    db.session.add(db_links)
                    db.session.commit()
                    print(response.url)
                except BadLinkException as e:
                    print(e)
                    db.session.rollback()
                    db_bad_links = BadLinks(word=self.word, reason=str(e),
                                            bad_link=response.url, source='Sciendo')
                    db.session.add(db_bad_links)
                    db.session.commit()
                except (psycopg2.errors.UniqueViolation, IntegrityError) as e:
                    print(e)
                    db.session.rollback()
                    db_bad_links = BadLinks(word=self.word,
                                            reason="Already in database",
                                            bad_link=response.url, source='Sciendo')
                    db.session.add(db_bad_links)
                    db.session.commit()
            else:
                db_bad_links = BadLinks(word=self.word,
                                        reason=f"Response code {response.status_code}", bad_link=response.url,
                                        source='Sciendo')
                db.session.add(db_bad_links)
                db.session.commit()
                db.session.close()


# Parser function for authors
def get_authors(authors_json):
    authors = []

    for i in range(len(authors_json)):
        authors.append(authors_json[i]['name']['given-names'] + " " + authors_json[i]['name']['surname'])

    return authors


# Parser function for citations
def get_citations(citations_json):
    citations = []

    for i in range(len(citations_json)):
        citations.append(citations_json[i]['citeString'])

    return citations
