import time
import psycopg2.errors

import requests
from bs4 import BeautifulSoup
import re
import yake
from app import db
from app.models import Links, Authors, Citations, Keywords, BadLinks, link_authors, link_keywords
from app.spiders.utils.bad_links_exception import BadLinkException
from app.spiders.utils.database_operations import remove_links_from_database, remove_bad_links_from_database


class Hindawi:
    def __init__(self, word: str):
        # Searched word
        self.word = word

    # Function for getting last page number
    def get_last_page(self):
        first_page = 1

        response = requests.get(f'https://www.hindawi.com/search/all/{self.word}/page/{first_page}/')

        if response.status_code == 200:
            html_content = BeautifulSoup(response.content, features='html.parser')
            try:
                last_page = html_content.find_all("li", class_="ant-pagination-item")[-1].text
            except:
                last_page = 0
            return last_page

    # Function for getting links from pagination
    def get_links(self):
        links = []
        last_page = int(self.get_last_page())
        print(f"Last page:{last_page}")

        # Return if there is no result
        if last_page == 0:
            return 0

        # Request for every page
        for page_number in range(1, last_page + 1):
            print(page_number)
            response = requests.get(f'https://www.hindawi.com/search/all/{self.word}/page/'+str(page_number)+'/')

            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                div = page.find_all("div", class_="ant-card-body")

                # Getting attribute a - links from page
                for a_link in div:
                    a = a_link.find('a', href=True)
                    if a is not None:
                        link = "https://www.hindawi.com" + a.attrs.get("href")
                        links.append(link)
                        print(link)
        print(f"Links count: ")
        print(len(links))
        return links

    # Function for scrapping information
    def scrape_links(self):
        # All scrapped links
        links = self.get_links()

        # No links found (no actual result on page)
        if len(links) == 0:
            return

        # Scrapping process
        for i in range(len(links)):
            response = requests.get(links[i])
            # Delay between requests for not overloading server
            time.sleep(0.4)

            # Status code OK
            if response.status_code == 200:
                # Parsing unicode not compatible characters
                try:
                    page = BeautifulSoup(response.content, features='html.parser')
                except UnicodeDecodeError:
                    page = BeautifulSoup(response.content, from_encoding='utf-8', errors='ignore')

                try:
                    # Link
                    link = response.url
                    # Image if is some
                    image = ""

                    # Description
                    description_tag = page.find("div", class_="articleBody")
                    # Checking all HTML elements for errors (missing)
                    if description_tag:
                        description_p_tag = description_tag.find("p")
                        if description_p_tag:
                            description = description_p_tag.text
                        else:
                            raise BadLinkException("Description missing")
                    else:
                        raise BadLinkException("Description missing")

                    # Article title
                    article_title_tag = page.find("h1", class_="articleHeader__title")
                    if article_title_tag:
                        article_title = article_title_tag.text
                    else:
                        raise BadLinkException("Article title missing")

                    # Published date
                    date_tag = page.find("div", class_="articleHeader__timeline_item articleHeader__timeline_item_sticky")
                    if date_tag:
                        date_span_tag = date_tag.find("span")
                        if date_span_tag:
                            date = date_span_tag.text
                        else:
                            raise BadLinkException("Published date missing")
                    else:
                        raise BadLinkException("Published date missing")

                    # Authors
                    authors_div_tag = page.find("div", class_="articleHeader__authors")
                    if authors_div_tag:
                        authors_span_tag = authors_div_tag.find_all("span", class_="articleHeader__authors_author")
                        if authors_span_tag:
                            authors_array = authors_span_tag
                        else:
                            raise BadLinkException("Authors missing")
                    else:
                        raise BadLinkException("Authors missing")

                    # Citations
                    citations_ol_tag = page.find("ol", class_="ArticleReferences_orderedReferences__mJr9M")
                    if citations_ol_tag:
                        citations_li_tag = citations_ol_tag.find_all("li", class_="ArticleReferences_articleReference__ouEuh")
                        if citations_li_tag:
                            citations_array = citations_li_tag
                        else:
                            raise BadLinkException("Citations missing")
                    else:
                        raise BadLinkException("Citations missing")

                    print(link)
                    # Add data to database (Links table)
                    db_citations = [Citations(reference=citation) for citation in get_citations(citations_array)]
                    db_links = Links(link=link, source='Hindawi', word=self.word, description=description, article_title=article_title, image=image, date=date)
                    db.session.add(db_links)
                    db.session.commit()

                    db_authors = [Authors(name=name, link_id=db_links.id) for name in get_authors(authors_array)]
                    db_keywords = [Keywords(word=keyword, link_id=db_links.id) for keyword in extract_keywords(description)]

                    db_links.authors = db_authors
                    db_links.keywords = db_keywords
                    db_links.citations = db_citations

                    db.session.add(db_links)
                    db.session.commit()
                # Add bad links to database with created exception as reason
                except BadLinkException as e:
                    print(e)
                    db.session.rollback()
                    db_bad_links = BadLinks(word=self.word, reason=str(e), bad_link=response.url, source='Hindawi')
                    db.session.add(db_bad_links)
                    db.session.commit()
                # Add bad links to database which are already scrapped (same results)
                except (psycopg2.errors.UniqueViolation, Exception) as e:
                    print(e)
                    db.session.rollback()
                    db_bad_links = BadLinks(word=self.word, reason="Already in database",
                                            bad_link=response.url, source='Hindawi')
                    db.session.add(db_bad_links)
                    db.session.commit()
                finally:
                    db.session.close()
            # Status code not OK - Add to table as BadLink
            else:
                db_bad_links = BadLinks(word=self.word, reason=f"Response code {response.status_code}", bad_link=response.url, source='Hindawi')
                db.session.add(db_bad_links)
                db.session.commit()
                db.session.close()


# Parser function for authors
def get_authors(authors_array):
    authors = []

    if authors_array:
        for author in authors_array:
            # Removing numbers
            full_author = re.sub("[1-9,]", "", author.text)
            # Removing sequention "and" before last author
            full_author = re.sub("and ", "", full_author)
            authors.append(full_author)
    else:
        raise BadLinkException("Authors missing")

    return authors


# Parser function for citations
def get_citations(citations_array):
    citations = []

    # Handling errors (missing HTML elements) in some articles
    if citations_array:
        for citation in citations_array:
            reference_tag = citation.find("div", class_="referenceContent")
            if reference_tag:
                reference_p_tag = reference_tag.find("p", class_="referenceText")
                if reference_p_tag:
                    reference = reference_p_tag.text
                    citations.append(reference)
                else:
                    raise BadLinkException("Citations missing")
            else:
                raise BadLinkException("Citations reference missing")
    else:
        raise BadLinkException("Citations missing")

    return citations


# Function for creating keywords
def extract_keywords(text):
    keywords = []

    if text:
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