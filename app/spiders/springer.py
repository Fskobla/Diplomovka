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
            response = requests.get(f'https://link.springer.com/search?new-search=true&query={self.word}&content-type=Article&sortBy=relevance&page={page_number}')
            print(page_number)
            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                div = page.find_all("a", class_="app-card-open__link")
                for a in div:
                    link = 'https://link.springer.com' + a.attrs.get("href")
                    links.append(link)
        return links

    def scrape_links(self):
        links = self.get_links()

        if len(links) == 0:
            return

        for i in range(len(links)):
            response = requests.get(links[i])
            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                print(i)
                try:
                    # Extracting data
                    link = response.url
                    image_picture_tag = page.find('picture')
                    if image_picture_tag:
                        image = image_picture_tag.find('img').attrs.get("src")

                    description_div_tag = page.find('div', class_='c-article-section__content')
                    if description_div_tag:
                        description = description_div_tag.find('p').text

                    article_title_header_tag = page.find('h1', class_="c-article-title")
                    if article_title_header_tag:
                        article_title = article_title_header_tag.text

                    date_tag = page.find("time")
                    if date_tag:
                        date = date_tag.text

                    authors_array = page.find_all("meta", {"name": "dc.creator"})
                    citations_ul_tag = page.find('ul', class_='c-article-references')
                    if citations_ul_tag:
                        citations = [li.find("p", class_='c-article-references__text').text for li in
                                     citations_ul_tag.find_all("li")] if citations_ul_tag else []

                    # Storing data in database
                    db_links = Links(link=link, source='Springer', word=self.word, description=description,
                                     article_title=article_title, image=image, date=date)
                    db.session.add(db_links)
                    db.session.commit()  # Commit the link to get the primary key

                    # Now db_links has an ID
                    db_authors = [Authors(name=name) for name in get_authors(authors_array)]
                    db_keywords = [Keywords(word=keyword) for keyword in extract_keywords(description)]

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
                db_bad_links = BadLinks(word=self.word,
                                        bad_link=response.url, source='Springer')
                db.session.add(db_bad_links)
                db.session.commit()
                db.session.close()


def get_authors(authors_array):
    authors = []

    if authors_array:
        for author in authors_array:
            author_tmp = author['content'].split(", ")
            author = (author_tmp[1] + " " + author_tmp[0]).strip()
            authors.append(author)
    else:
        raise BadLinkException("Authors missing")
    return authors


# Function for creating keywords
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