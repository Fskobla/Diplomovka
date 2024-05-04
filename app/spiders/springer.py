import logging
import time

import requests
import yake
from bs4 import BeautifulSoup
import psycopg2.errors

from app import db
from app.models import Citations, Links, Authors, Keywords, BadLinks
from app.spiders.utils.bad_links_exception import BadLinkException


class Springer:
    def __init__(self, word: str):
        self.word = word

    def get_links(self):
        links = []
        # Only 1000 results possible to shown
        last_page = 50

        for page_number in range(1, last_page+1):
            response = requests.get(f'https://link.springer.com/search?new-search=true&query={self.word}&content-type=Article&sortBy=relevance&page={page_number}',
                                    proxies={
                                        "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                                        "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
                                    }
                                    )
            print(page_number)
            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                div = page.find_all("a", class_="app-card-open__link")
                if div:
                    for a in div:
                        link = 'https://link.springer.com' + a.attrs.get("href")
                        print(link)
                        links.append(link)
                else:
                    break
        return links

    def scrape_links(self):
        links = self.get_links()

        if len(links) == 0:
            return

        for link in links:
            try:
                response = requests.get(link, proxies={
                    "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                    "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
                })
            except Exception as e:
                self.add_to_bad_links(link, "Bad link url")
                continue

            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser', from_encoding='utf-8')

                try:
                    # Scraping data
                    link_data = self.scrape_link_data(page, response.url)

                    # Add data to database
                    self.add_to_database(link, link_data)
                except Exception as e:
                    print(e)
                    continue  # Skip this link and continue with the next one
            else:
                self.add_to_bad_links(response.url, f"Response code {response.status_code}")


    def scrape_description(self, page):
        try:
            description_div_tag = page.find('div', class_='c-article-section__content')
            if description_div_tag:
                description_p_tag = description_div_tag.find('p')
                if description_p_tag:
                    return description_p_tag.text
        except Exception as e:
            print(e)
        return None

    def scrape_image(self, page):
        try:
            image_picture_tag = page.find('picture')
            if image_picture_tag:
                return image_picture_tag.find('img').attrs.get("src")
        except Exception as e:
            print(e)
        return None

    def scrape_authors(self, page):
        authors = []
        try:
            authors_array = page.find_all("meta", {"name": "dc.creator"})
            if authors_array:
                for author in authors_array:
                    author_tmp = author['content'].split(", ")
                    author = (author_tmp[1] + " " + author_tmp[0]).strip()
                    authors.append(author)
        except Exception as e:
            print(e)
        return authors

    def scrape_article_title(self, page):
        try:
            article_title_tag = page.find('h1', class_="c-article-title")
            if article_title_tag:
                return article_title_tag.text
        except Exception as e:
            print(e)
        return None

    def scrape_date(self, page):
        try:
            date_tag = page.find("time")
            if date_tag:
                date = date_tag.text
                return date
        except Exception as e:
            print(e)
        return None

    def scrape_citations(self, page):
        citations = []

        citations_ol_tag = page.find('ol', class_='c-article-references')
        if citations_ol_tag:
            citations_list_tag = citations_ol_tag
        else:
            citations_list_tag = page.find('ul', class_='c-article-references')

        try:
            if citations_list_tag:
                citations_li_tags = citations_list_tag.find_all("li")
                for citation_li_tag in citations_li_tags:
                    reference_p_tag = citation_li_tag.find("p", class_='c-article-references__text')
                    if reference_p_tag:
                        citations.append(reference_p_tag.text)
        except Exception as e:
            print(e)

        return citations

    def scrape_keywords(self, page):
        keywords = []
        try:
            actual_keyword = page.find_all('a', {'data-track-action': 'view keyword'})
            if actual_keyword:
                for selected_keyword in actual_keyword:
                    print(selected_keyword.text)
                    keywords.append(selected_keyword.text)
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

    def scrape_link_data(self, page, url):
        data = {}

        # Scraping link, description, article title, image, date, authors, keywords, and citations
        data['link'] = url
        data['image'] = self.scrape_image(page)
        data['description'] = self.scrape_description(page)
        data['article_title'] = self.scrape_article_title(page)
        data['date'] = self.scrape_date(page)
        data['authors'] = self.scrape_authors(page)
        data['citations'] = self.scrape_citations(page)
        data['keywords'] = self.scrape_keywords(page)
        if not data['keywords'] and data['description'] is not None:
            data['keywords'] = self.extract_keywords(data['description'])

        return data

    def add_to_bad_links(self, link, reason):
        db_bad_link = BadLinks(word=self.word, bad_link=link, source='Springer', reason=reason)
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

        db_links = Links(link=link, source='Springer', word=self.word, description=link_data['description'],
                         article_title=link_data['article_title'], image="", date=link_data['date'])
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
