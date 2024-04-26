from flask import render_template, request, redirect, url_for, jsonify, abort
from datetime import datetime

from sqlalchemy import text, func

from . import create_app
from app.spiders.hindawi import Hindawi
from app.spiders.sciendo import Sciendo
import time
from app import db
from app.models import Links, Keywords, Authors, Citations


def init_app_routes(app):
    @app.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            word = request.form.get('search_word')
            hindawi_value = request.form.get('hindawi_value')
            sciendo_value = request.form.get('sciendo_value')
            print(sciendo_value)
            print(hindawi_value)
            print("SLOVO:",word)
            if word != '':
                print("SOM TU")
                if hindawi_value is None and sciendo_value is None:
                    print("OBOJE NULL")
                    return render_template('index.html')
                if hindawi_value == 'true':
                    print("HINDAWI")
                    hindawi = Hindawi(word)
                    hindawi.scrape_links()
                if sciendo_value == 'true':
                    print("SCIENDO")
                    sciendo = Sciendo(word)
                    sciendo.scrape_links()
                return redirect(url_for('literature', word=word))
        return render_template('index.html')

    @app.route('/graph')
    def graph():
        word = request.args.get('word')  # Get the word from the query parameters
        if word:
            return render_template('graph.html', word=word)  # Pass the word to the template
        else:
            # Handle the case where word is not provided
            # Redirect back to the literature page or display an error message
            return redirect(url_for('literature'))

    @app.route('/literature', methods=['GET','POST'])
    def literature():
        word = request.args.get('word')
        if word:
            links = Links.query.filter_by(word=word).all()
            if len(links) == 0:
                abort(404)
            return render_template('literature.html', links=links, word=word)
        else:
            abort(404)

    @app.route('/get_articles_per_year')
    def get_articles_per_year():
        word = request.args.get('word')
        if word:
            # Query database to get count of articles per year for the given word
            articles = Links.query.filter(Links.word == word).all()

            # Extract the last 4 characters from the date string to get the year
            years = [int(article.date[-4:]) for article in articles]

            # Count articles per year
            articles_per_year = {}
            for year in years:
                articles_per_year[year] = articles_per_year.get(year, 0) + 1

            return jsonify(articles_per_year)
        else:
            return jsonify({"error": "Word parameter missing"}), 400

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('page_404.html', title='404'), 404
