from flask import render_template, request, redirect, url_for, jsonify
from . import create_app
from app.spiders.hindawi import Hindawi
from app.spiders.sciendo import Sciendo
import time
from app import db
from app.models import Links, Keywords, Authors, Citations


def init_app_routes(app):
    @app.route('/', methods=['GET', 'POST'])
    def index():
        start = time.time()
        if request.method == 'POST':
            word = request.form.get('search_word')
            if word is not None:
                if request.form.get('hindawi_value') == 'true':
                    hindawi = Hindawi(word)
                    hindawi.scrape_links()
                if request.form.get('sciendo_value') == 'true':
                    sciendo = Sciendo(word)
                    sciendo.scrape_links()
                return redirect(url_for('literature', word=word))
        return render_template('index.html')

    @app.route('/graph')
    def graph():
        return render_template('graph.html')

    @app.route('/literature')
    def literature():
        word = request.args.get('word')
        links = Links.query.filter_by(word=word).all()
        print(links)
        return jsonify([link.to_dict() for link in links])
