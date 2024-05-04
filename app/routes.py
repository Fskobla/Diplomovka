import asyncio
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import networkx as nx
from flask import render_template, request, redirect, url_for, jsonify, abort, send_file
from matplotlib import pyplot as plt

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
            proxy_value = request.form.get('proxy_value')
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
                    hindawi = Hindawi(word, proxy_value)
                    await hindawi.scrape_links()

                async def scrape_sciendo():
                    sciendo = Sciendo(word, proxy_value)
                    await sciendo.scrape_links()

                async def scrape_springer():
                    springer = Springer(word, proxy_value)
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

    @app.route('/graph_co_occurence', methods=['GET'])
    def get_co_occurrence():
        word = request.args.get('word')
        min_occurrences = 2

        links = Links.query.filter(Links.word == word).all()

        G = nx.Graph()
        keyword_map = {}
        keyword_frequency = defaultdict(int)

        # Create graph and populate keyword_map and keyword_frequency
        for link in links:
            article_node = f"{link.id}"
            has_keyword = False  # Flag to check if the link has any keywords
            for keyword in link.keywords:
                keyword_name = keyword.word
                has_keyword = True
                if keyword_name not in keyword_map:
                    keyword_node = f"{keyword_name}"
                    G.add_node(keyword_node)
                    keyword_map[keyword_name] = keyword_node
                else:
                    keyword_node = keyword_map[keyword_name]
                G.add_edge(article_node, keyword_node)
                keyword_frequency[keyword_name] += 1

            # If the link has no keywords, don't add it to the graph
            if has_keyword:
                G.add_node(article_node)
                # Set attribute to identify link.id nodes
                G.nodes[article_node]['type'] = 'link.id'

        # Remove nodes based on minimum occurrence
        nodes_to_remove = [keyword_name for keyword_name, frequency in keyword_frequency.items() if
                           frequency < min_occurrences]
        G.remove_nodes_from(nodes_to_remove)

        link_ids_to_remove = []
        for node in G.nodes():
            if G.nodes[node].get('type') == 'link.id':
                if G.degree(node) == 0:
                    link_ids_to_remove.append(node)
        G.remove_nodes_from(link_ids_to_remove)

        plt.figure(figsize=(19, 10))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=False, node_size=50)

        # Change color of link.id nodes
        node_colors = ['orange' if G.nodes[node].get('type') == 'link.id' else 'skyblue' for node in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=50)

        for keyword_name, keyword_node in keyword_map.items():
            if keyword_name not in nodes_to_remove:
                frequency = keyword_frequency[keyword_name]
                if frequency <= 5:
                    text_size = (frequency * 3) + 2
                elif 5 < frequency <= 10:
                    text_size = (frequency * 3) + 1
                elif 10 < frequency <= 20:
                    text_size = (frequency * 3) + 0.5
                else:
                    text_size = (frequency * 3) + 0.25

                plt.text(pos[keyword_node][0], pos[keyword_node][1], keyword_name, fontsize=text_size, ha='center')

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            plt.savefig(temp_file.name)

        plt.close()

        return send_file(temp_file.name, mimetype='image/png')

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
