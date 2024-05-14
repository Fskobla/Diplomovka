import json
import logging
import random
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
    def __init__(self, word: str, proxy):
        self.word = word
        self.proxy = proxy

    def get_links(self):
        links = []

        page_number = 0
        while True:
            params = {
                'commonSearchText': {self.word},
                'page': str(page_number),
                'packageType': 'Article'
            }

            if self.proxy == 'true':
                response = requests.get('https://intapi.sciendo.com/search/filterData', params=params, headers=get_headers(), proxies={
                                            "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                                            "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
                                        })
            else:
                time.sleep(0.4)
                response = requests.get('https://intapi.sciendo.com/search/filterData', params=params, headers=get_headers())

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

        for i in range(len(links)):
            if self.proxy == 'true':
                response = requests.get(links[i], headers=get_headers(), proxies={
                                            "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                                            "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
                                        })
            else:
                time.sleep(0.4)
                response = requests.get(links[i], headers=get_headers())

            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                try:
                    data = json.loads(page.find('script', id="__NEXT_DATA__", type='application/json').text.encode('utf-8', 'ignore'))

                    link_data = self.scrape_link_data(data, response.url)

                    # Add data to database
                    self.add_to_database(response.url, link_data)
                except Exception as e:
                    print(e)
                    continue  # Skip this link and continue with the next one
            else:
                self.add_to_bad_links(response.url, f"Response code {response.status_code}")


    def scrape_link_data(self, page, url):
        data = {}

        # Scraping link, description, article title, date, authors, keywords, and citations
        data['link'] = url
        data['description'] = self.scrape_description(page)
        data['article_title'] = self.scrape_article_title(page)
        data['image'] = self.scrape_image(page)
        data['date'] = self.scrape_date(page)
        data['authors'] = self.scrape_authors(page)
        data['citations'] = self.scrape_citations(page)
        data['keywords'] = self.scrape_keywords(page)
        if not data['keywords'] and data['description'] is not None:
            data['keywords'] = self.extract_keywords(data['description'])

        return data

    def scrape_article_title(self, data):
        try:
            article_title = data['props']['pageProps']['product']['articleData']['articleTitle']
            return article_title
        except Exception as e:
            print(e)
        return None


    def scrape_description(self, data):
        try:
            description = data['props']['pageProps']['product']['longDescription']
            return description
        except Exception as e:
            print(e)
        return None

    def scrape_image(self, data):
        try:
            image = data['props']['pageProps']['product']['coverUrl']
            return image
        except Exception as e:
            print(e)
        return None

    def scrape_authors(self, data):
        authors = []
        try:
            authors_array = data['props']['pageProps']['product']['articleData']['contribGroup']['contrib']
            for i in range(len(authors_array)):
                authors.append(authors_array[i]['name']['given-names'] + " " + authors_array[i]['name']['surname'])
        except Exception as e:
            print(e)
        return authors

    def scrape_date(self, data):
        try:
            date = data['props']['pageProps']['product']['articleData']['publishedDate']
            return date
        except Exception as e:
            print(e)

    def scrape_citations(self, data):
        citations = []
        try:
            citations_array = data['props']['pageProps']['product']['articleData']['referenceList']
            for i in range(len(citations_array)):
                citations.append(citations_array[i]['citeString'])
        except Exception as e:
            print(e)
        return citations

    def scrape_keywords(self, data):
        keywords = []
        try:
            keywords = data['props']['pageProps']['product']['articleData']['keywords']
        except Exception as e:
            print(e)
        return keywords

    def extract_keywords(self, text):
        keywords = []

        if text is not None:
            language = "en"
            # Max length of keyword = 2
            max_ngram_size = 2
            # Parameter for duplications in keywords
            deduplication_thresold = 0.9
            deduplication_algo = 'seqm'
            window_size = 1
            # Max keywords = 7
            num_of_keywords = 7

            custom_kw_extractor = yake.KeywordExtractor(lan=language, n=max_ngram_size, dedupLim=deduplication_thresold,
                                                        dedupFunc=deduplication_algo, windowsSize=window_size,
                                                        top=num_of_keywords,
                                                        features=None)
            all_keywords = custom_kw_extractor.extract_keywords(text)

            for kw, s in all_keywords:
                # At least 1% similarity
                if s > 0.01:
                    keywords.append(kw)

        return keywords

    def add_to_bad_links(self, link, reason):
        db_bad_link = BadLinks(word=self.word, bad_link=link, source='Sciendo', reason=reason)
        db.session.add(db_bad_link)
        db.session.commit()

    def check_link_data(self, link, link_data):

        if link_data['description'] is None:
            self.add_to_bad_links(link, "Description missing")
            return False
        elif link_data['article_title'] is None:
            self.add_to_bad_links(link, "Article title missing")
            return False
        elif link_data['date'] is None:
            self.add_to_bad_links(link, "Published date missing")
            return False
        elif not link_data['authors']:
            self.add_to_bad_links(link, "Authors missing")
            return False
        elif not link_data['citations']:
            self.add_to_bad_links(link, "Citations missing")
            return False
        elif not link_data['keywords']:
            self.add_to_bad_links(link, "Keywords missing")
            return False
        else:
            return True
    def add_to_database(self, link, link_data):
        existing_link = Links.query.filter_by(link=link).first()
        if existing_link:
            self.add_to_bad_links(link, "Already in database")
            return
        if not self.check_link_data(link, link_data):
            return

        db_links = Links(link=link, source='Sciendo', word=self.word, description=link_data['description'],
                         article_title=link_data['article_title'], image=link_data['image'], date=link_data['date'])
        db.session.add(db_links)
        db.session.commit()  # Commit the link to get the primary key

        db_authors = [Authors(name=name) for name in link_data['authors']]
        db.session.add_all(db_authors)
        db.session.commit()

        db_citations = [Citations(reference=reference) for reference in link_data['citations']]
        db.session.add_all(db_citations)
        db.session.commit()

        db_keywords = [Keywords(word=word) for word in link_data['keywords']]
        db.session.add_all(db_keywords)
        db.session.commit()

        # Associate authors and citations with the link
        db_links.authors.extend(db_authors)
        db_links.citations.extend(db_citations)
        db_links.keywords.extend(db_keywords)

        db.session.commit()

def get_headers():
    headers = []
    mozzilla_headers = {
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
    headers.append(mozzilla_headers)

    chrome_headers = {
        'accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }
    headers.append(chrome_headers)

    edge_headers = {
        'accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'sk,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
    }
    headers.append(edge_headers)

    header = random.choice(headers)

    return header
