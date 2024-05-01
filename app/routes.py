import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from flask import render_template, request, redirect, url_for, jsonify, abort
from app.spiders.hindawi import Hindawi
from app.spiders.sciendo import Sciendo
from app.models import Links, BadLinks
from app import db
from app.spiders.springer import Springer
from app.spiders.utils.database_operations import remove_links_from_database, remove_bad_links_from_database


def init_app_routes(app):
    def run_async_function_in_thread(func, *args, **kwargs):
        with app.app_context():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.set_debug(True)
            try:
                result = loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()
            return result

    @app.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            word = request.form.get('search_word')
            word = str.lower(word)
            hindawi_value = request.form.get('hindawi_value')
            sciendo_value = request.form.get('sciendo_value')
            springer_value = request.form.get('springer_value')
            print(sciendo_value)
            print(hindawi_value)
            print(springer_value)
            print("SLOVO:", word)
            if word != '':
                print("SOM TU")
                remove_bad_links_from_database(db, word)
                remove_links_from_database(db, word)
                if hindawi_value is None and sciendo_value is None and springer_value is None:
                    print("OBOJE NULL")
                    return render_template('index.html')

                async def scrape_hindawi():
                    hindawi = Hindawi(word)
                    await hindawi.scrape_links()

                async def scrape_sciendo():
                    sciendo = Sciendo(word)
                    await sciendo.scrape_links()

                async def scrape_springer():
                    springer = Springer(word)
                    await springer.scrape_links()

                # Execute scraping tasks concurrently using asyncio within threads
                with ThreadPoolExecutor() as executor:
                    tasks = []
                    if hindawi_value == 'true':
                        print("HINDAWI")
                        tasks.append(partial(run_async_function_in_thread, scrape_hindawi))
                    if sciendo_value == 'true':
                        print("SCIENDO")
                        tasks.append(partial(run_async_function_in_thread, scrape_sciendo))
                    if springer_value == 'true':
                        print("SPRINGER")
                        tasks.append(partial(run_async_function_in_thread, scrape_springer))

                    # Run scraping tasks concurrently
                    for task in tasks:
                        executor.submit(task)

                return redirect(url_for('literature', word=word))
        return render_template('index.html')

    @app.route('/graph')
    def graph():
        word = request.args.get('word')
        word = str.lower(word)
        articles = Links.query.filter(Links.word == word).all()
        if word and len(articles) != 0:
            return render_template('graph.html', word=word)
        else:
            abort(404)

    @app.route('/top_results')
    def top_results():
        word = request.args.get('word')
        word = str.lower(word)
        articles = Links.query.filter(Links.word == word).all()
        if word and len(articles) != 0:
            return render_template('top_results.html', word=word)
        else:
            abort(404)



    @app.route('/literature', methods=['GET', 'POST'])
    def literature():
        word = request.args.get('word')
        word = str.lower(word)
        if word:
            links = Links.query.filter_by(word=word).all()
            if len(links) == 0:
                abort(404)
            return render_template('literature.html', links=links, word=str.lower(word))
        else:
            abort(404)

    @app.route('/get_articles_per_year')
    def get_articles_per_year():
        word = request.args.get('word')
        word = str.lower(word)
        if word:
            articles = Links.query.filter(Links.word == word).all()

            years = [int(article.date[-4:]) for article in articles]

            articles_per_year = {}
            for year in years:
                articles_per_year[year] = articles_per_year.get(year, 0) + 1

            return jsonify(articles_per_year)
        else:
            return jsonify({"error": "Word parameter missing"}), 400

    @app.route('/get_bad_links_by_word')
    def get_bad_links_by_word():
        word = request.args.get('word')
        word = str.lower(word)
        if word:
            bad_links = BadLinks.query.filter(BadLinks.word == word).all()

            # Construct response JSON
            response = []
            for link in bad_links:
                response.append({
                    'bad_link': link.bad_link,
                    'source': link.source,
                    'reason': link.reason
                })

            return jsonify(response)
        else:
            return jsonify({"error": "Word parameter missing"}), 400

    @app.route('/get_co_occurrence_data')
    def get_co_occurrence_data():
        word = request.args.get('word')
        word = str.lower(word)
        if word:
            articles = Links.query.filter_by(word=word).all()
            co_occurrence_data = {}

            for article in articles:
                keywords_in_article = [keyword.word for keyword in article.keywords if keyword.word != word]
                for keyword in keywords_in_article:
                    if article.link not in co_occurrence_data:
                        co_occurrence_data[article.link] = {}
                    if keyword not in co_occurrence_data[article.link]:
                        co_occurrence_data[article.link][keyword] = 0
                    co_occurrence_data[article.link][keyword] += 1

            co_occurrence_data = {link: keywords for link, keywords in co_occurrence_data.items()
                                  if len(keywords) > 1
                                  and not all(count == 1 for count in keywords.values())}

            return jsonify(co_occurrence_data)
        else:
            return jsonify({"error": "Word parameter missing"}), 400

    @app.route('/top_keywords', methods=['GET'])
    def top_keywords():
        # Get the selected word from the query parameters
        word = request.args.get('word')
        word = str.lower(word)
        if not word:
            return jsonify({"error": "Word parameter is missing"}), 400

        # Query the database to get all links related to the selected word
        links = Links.query.filter_by(word=word).all()

        # Extract keywords from each link and count their occurrences
        all_keywords = []
        for link in links:
            all_keywords.extend(keyword.word for keyword in link.keywords)

        keyword_counts = Counter(all_keywords)

        # Get the top 10 most frequent keywords
        top_10_keywords = keyword_counts.most_common(10)

        # Return the result as JSON
        return jsonify({"top_keywords": top_10_keywords})

    @app.route('/top_authors', methods=['GET'])
    def top_authors():
        # Get the selected word from the query parameters
        word = request.args.get('word')
        word = str.lower(word)
        if not word:
            return jsonify({"error": "Word parameter is missing"}), 400

        # Query the database to get all links related to the selected word
        links = Links.query.filter_by(word=word).all()

        # Extract authors from each link and count their occurrences
        all_authors = []
        for link in links:
            all_authors.extend(author.name for author in link.authors)

        author_counts = Counter(all_authors)

        # Get the top 10 most frequent authors
        top_10_authors = author_counts.most_common(10)

        # Return the result as JSON
        return jsonify({"top_authors": top_10_authors})

    @app.route('/top_articles_with_most_citations', methods=['GET'])
    def top_articles_with_most_citations():
        # Get the word from the query parameters
        word = request.args.get('word')
        word = str.lower(word)

        if not word:
            return jsonify({"error": "Word parameter is missing"}), 400

        # Query the database to get all articles related to the word
        articles = Links.query.filter_by(word=word).all()

        if not articles:
            return jsonify({"error": f"No articles found for the word '{word}'"}), 404

        # Sort the articles based on the number of citations (descending order)
        sorted_articles = sorted(articles, key=lambda x: len(x.citations), reverse=True)

        # Get the top 10 articles with the most citations
        top_10_articles = sorted_articles[:10]

        # Prepare the response data
        response_data = [{
            'article_title': article.article_title,
            'citations_count': len(article.citations)
        } for article in top_10_articles]

        # Return the result as JSON
        return jsonify({"top_articles_with_most_citations": response_data})

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('page_404.html', title='404'), 404
