from flask import render_template, request
from . import create_app
from app.spiders.hindawi import Hindawi
from app.spiders.sciendo import Sciendo
import time


def init_app_routes(app):
    @app.route('/', methods=['GET', 'POST'])
    def index():
        start = time.time()
        if request.method == 'POST':
            word = request.form.get('search_word')
            print(word)
            print(request.form.get('hindawi_value'))
            if request.form.get('hindawi_value') == 'true':
                hindawi = Hindawi(word)
                hindawi.scrape_links()
            if request.form.get('sciendo_value') == 'true':
                sciendo = Sciendo(word)
                sciendo.scrape_links()
        end = time.time()
        print(end - start)
        return render_template('index.html')

    @app.route('/graph')
    def graph():
        return render_template('graph.html')

    @app.route('/literature')
    def literature():
        return render_template('literature.html')
