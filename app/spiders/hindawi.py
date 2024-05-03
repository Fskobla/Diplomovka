import re
import time
import requests
import yake
from bs4 import BeautifulSoup
from app import db
from app.models import Links, Authors, Citations, Keywords, BadLinks


class Hindawi:
    def __init__(self, word: str):
        # Searched word
        self.word = word

    # Function for getting last page number
    def get_last_page(self):
        first_page = 1

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'sk,en-US;q=0.7,en;q=0.3',
            'Alt-Used': 'www.hindawi.com',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Priority': 'u=1',
        }

        response = requests.get(f'https://www.hindawi.com/search/all/{self.word}/page/{str(first_page)}/', headers=headers, proxies={
                                        "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                                        "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
                                    })

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

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'sk,en-US;q=0.7,en;q=0.3',
            'Alt-Used': 'www.hindawi.com',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Priority': 'u=1',
        }


        # Return if there is no result
        if last_page == 0:
            return 0

        # Request for every page
        for page_number in range(1, last_page + 1):
            print(page_number)
            response = requests.get(f'https://www.hindawi.com/search/all/{self.word}/page/' + str(page_number) + '/', headers=headers,
                                    proxies={
                                        "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                                        "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
                                    })
            print(response.status_code)
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'sk,en-US;q=0.7,en;q=0.3',
            'Alt-Used': 'www.hindawi.com',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Priority': 'u=1',
        }

        # No links found (no actual result on page)
        if len(links) == 0:
            return

        # Scrapping process
        for link in links:
            response = requests.get(link, headers=headers, proxies={
                "http": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/",
                "https": "http://eapxljvu-rotate:jvhx8t1hltjj@p.webshare.io:80/"
            })
            # Delay between requests for not overloading server
            #time.sleep(0.4)
            print(link)
            # Status code OK
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

    # Function to scrape data from a single link
    def scrape_link_data(self, page, url):
        data = {}

        # Scraping link, description, article title, date, authors, keywords, and citations
        data['link'] = url
        data['description'] = self.scrape_description(page)
        data['article_title'] = self.scrape_article_title(page)
        data['date'] = self.scrape_date(page)
        data['authors'] = self.scrape_authors(page)
        data['citations'] = self.scrape_citations(page)
        data['keywords'] = self.extract_keywords(data['description'])

        return data

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

    # Function to scrape description from page
    def scrape_description(self, page):
        try:
            description_tag = page.find("div", class_="articleBody")
            if description_tag:
                description_p_tag = description_tag.find("p")
                if description_p_tag:
                    return description_p_tag.text
        except UnicodeDecodeError:
            print("Unicode decode error occurred while scraping description.")
        return None

    # Function to scrape article title from page
    def scrape_article_title(self, page):
        try:
            article_title_tag = page.find("h1", class_="articleHeader__title")
            if article_title_tag:
                return article_title_tag.text
        except UnicodeDecodeError:
            print("Unicode decode error occurred while scraping article title.")
        return None

    # Function to scrape date from page
    def scrape_date(self, page):
        try:
            date_tag = page.find("div", class_="articleHeader__timeline_item articleHeader__timeline_item_sticky")
            if date_tag:
                date_span_tag = date_tag.find("span")
                if date_span_tag:
                    return date_span_tag.text
        except UnicodeDecodeError:
            print("Unicode decode error occurred while scraping date.")
        return None

    # Function to scrape authors from page
    def scrape_authors(self, page):
        try:
            authors_array = []
            authors_div_tag = page.find("div", class_="articleHeader__authors")
            if authors_div_tag:
                authors_span_tag = authors_div_tag.find_all("span", class_="articleHeader__authors_author")
                if authors_span_tag:
                    return [re.sub("[1-9,]|and ", "", author.text) for author in authors_span_tag]
        except UnicodeDecodeError:
            print("Unicode decode error occurred while scraping authors.")
        return []

    # Function to scrape citations from page
    def scrape_citations(self, page):
        citations = []

        try:
            citations_ol_tag = page.find("ol", class_="ArticleReferences_orderedReferences__mJr9M")
            if citations_ol_tag:
                citations_li_tags = citations_ol_tag.find_all("li", class_="ArticleReferences_articleReference__ouEuh")
                for citation_li_tag in citations_li_tags:
                    reference_p_tag = citation_li_tag.find("div", class_="referenceContent").find("p",
                                                                                                  class_="referenceText")
                    if reference_p_tag:
                        citations.append(reference_p_tag.text)
        except UnicodeDecodeError:
            print("Unicode decode error occurred while scraping citations.")

        return citations

    def add_to_bad_links(self, link, reason):
        db_bad_link = BadLinks(word=self.word, bad_link=link, source='Hindawi', reason=reason)
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

    # Function to add data to database
    def add_to_database(self, link, link_data):
        existing_link = Links.query.filter_by(link=link).first()
        if existing_link:
            self.add_to_bad_links(link, "Already in database")
            return
        if not self.check_link_data(link, link_data):
            return

        db_links = Links(link=link, source='Hindawi', word=self.word, description=link_data['description'],
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
