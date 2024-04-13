import time
import requests
from bs4 import BeautifulSoup
import re
import yake
from app import db
from models import Links,Authors,Citations,Keywords


class Hindawi:
    def __init__(self, word: str):
        self.word = word
        self.bad_links = 0

    def get_last_page(self):
        first_page = 1

        response = requests.get(f'https://www.hindawi.com/search/all/{self.word}/page/{first_page}/')

        if response.status_code == 200:
            html_content = BeautifulSoup(response.content, features='html.parser')
            last_page = html_content.find_all("li", class_="ant-pagination-item")[-1].text
            return last_page

    def get_links(self):
        links = []
        last_page = int(self.get_last_page())
        print(f"Last page:{last_page}")
        for page_number in range(1, last_page + 1):
            print(page_number)
            response = requests.get(f'https://www.hindawi.com/search/all/{self.word}/page/'+str(page_number)+'/',proxies={
                            "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                            "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
            })
            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')
                div = page.find_all("div", class_="ant-card-body")

                for a_link in div:
                    a = a_link.find('a', href=True)
                    if a is not None:
                        link = "https://www.hindawi.com" + a.attrs.get("href")
                        links.append(link)
                        print(link)
        print(f"Links count: ")
        print(len(links))
        return links

    def scrape_links(self):
        bad_links = 0
        links = self.get_links()

        for i in range(len(links)):
            response = requests.get(links[i], proxies={
                            "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                            "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
            })
            if response.status_code == 200:
                page = BeautifulSoup(response.content, features='html.parser')

                try:
                    link = response.url
                    description = page.find("div", class_="articleBody").find("p").text
                    article_title = page.find("h1", class_="articleHeader__title").text
                    authors_array = page.find("div", class_="articleHeader__authors").find_all("span",
                                                                                               class_="articleHeader__authors_author")
                    date = page.find("div",
                                     class_="articleHeader__timeline_item articleHeader__timeline_item_sticky").find(
                        "span").text
                    image = ""
                    citations_array = page.find("ol", class_="ArticleReferences_orderedReferences__mJr9M").find_all(
                        "li", class_="ArticleReferences_articleReference__ouEuh")
                    
                    print(link)
                    db_links = Links(link=link, description=description, article_title=article_title, image=image, date=date)
                    try:
                        db.session.add(db_links)
                        db.session.commit()
                        get_citations(citations_array, db_links)
                        get_authors(authors_array, db_links)
                        extract_keywords(description, db_links)
                    except:
                        print(f"PASSED {link}")
                        pass
                except Exception as e:
                    print(e)
                    db.session.rollback()
                    bad_links = bad_links + 1
                finally:
                    db.session.close()


def get_authors(authors_array, db_links):
    for author in authors_array:
        full_author = re.sub("[1-9,]", "", author.text)
        full_author = re.sub("and ", "", full_author)
        db_authors = Authors(name=full_author, link_id=db_links.id)
        db.session.add(db_authors)
        db.session.commit()



def get_citations(citations_array, db_links):
    for citation in citations_array:
        reference = citation.find("div", class_="referenceContent").find("p", class_="referenceText").text
        db_citations = Citations(reference=reference, link_id=db_links.id)
        db.session.add(db_citations)
        db.session.commit()


def extract_keywords(text, db_links):
    language = "en"
    max_ngram_size = 3
    deduplication_thresold = 0.9
    deduplication_algo = 'seqm'
    window_size = 1
    num_of_keywords = 10

    custom_kw_extractor = yake.KeywordExtractor(lan=language, n=max_ngram_size, dedupLim=deduplication_thresold,
                                                dedupFunc=deduplication_algo, windowsSize=window_size, top=num_of_keywords,
                                                features=None)
    all_keywords = custom_kw_extractor.extract_keywords(text)

    for kw, s in all_keywords:
        if s > 0.01:
            keyword = Keywords(word=kw, link_id=db_links.id)
            db.session.add(keyword)
            db.session.commit()