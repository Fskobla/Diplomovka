import json
import logging
import time

import requests
import yake
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
                    link = response.url

                    # Image if exists
                    image = data['props']['pageProps']['product']['coverUrl']

                    # Published date
                    date = data['props']['pageProps']['product']['articleData']['publishedDate']

                    # Description
                    description = data['props']['pageProps']['product']['longDescription']
                    if isinstance(description, list):
                        description = [d.encode('utf-8', 'ignore').decode('utf-8', 'ignore') for d in description]
                    else:
                        description = description.encode('utf-8', 'ignore').decode('utf-8', 'ignore')

                    # Article_title
                    article_title = data['props']['pageProps']['product']['articleData']['articleTitle']

                    # Authors
                    authors = get_authors(
                            data['props']['pageProps']['product']['articleData']['contribGroup']['contrib'])

                    # Keywords
                    if data['props']['pageProps']['product']['articleData']['keywords'] and description:
                        keywords = data['props']['pageProps']['product']['articleData']['keywords']
                    else:
                        keywords = extract_keywords(description)

                    # Citations
                    citations = get_citations(data['props']['pageProps']['product']['articleData']['referenceList'])

                    db_links = Links(link=link, source='Springer', word=self.word, description=description,
                                     article_title=article_title, image=image, date=date)
                    db.session.add(db_links)
                    db.session.commit()  # Commit the link to get the primary key

                    # Now db_links has an ID
                    db_authors = [Authors(name=name) for name in authors]
                    db_keywords = [Keywords(word=keyword) for keyword in keywords]

                    # Associate authors and keywords with the link
                    db_links.authors.extend(db_authors)
                    db_links.keywords.extend(db_keywords)
                    db_links.citations = [Citations(reference=citation) for citation in citations]

                    # Add the authors, keywords, and citations to the session and commit
                    db.session.add_all(db_authors)
                    db.session.add_all(db_keywords)
                    db.session.commit()
                except Exception as e:
                    logging.error(f"Error processing link {link}: {e}")
                    db.session.rollback()
                    if BadLinks.query.filter_by(bad_link=link).first() is not None:
                        continue
                    else:
                        db_bad_links = BadLinks(word=self.word, bad_link=link, source='Springer')
                        db.session.add(db_bad_links)
                        db.session.commit()
                finally:
                    db.session.close()

            else:
                db_bad_links = BadLinks(word=self.word, bad_link=response.url,
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

def extract_keywords(text):
    keywords = []

    if text != "":
        language = "en"
        # Max length of keyword = 2
        max_ngram_size = 2
        # Parameter for duplications in keywords
        deduplication_thresold = 0.9
        deduplication_algo = 'seqm'
        window_size = 1
        # Max keywords = 10
        num_of_keywords = 10

        custom_kw_extractor = yake.KeywordExtractor(lan=language, n=max_ngram_size, dedupLim=deduplication_thresold,
                                                    dedupFunc=deduplication_algo, windowsSize=window_size, top=num_of_keywords,
                                                    features=None)
        all_keywords = custom_kw_extractor.extract_keywords(text)

        for kw, s in all_keywords:
            # At least 1% similarity
            if s > 0.01:
                keywords.append(kw)

    return keywords