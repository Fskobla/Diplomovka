from flask import render_template, request
from spiders.hindawi import Hindawi
import time


def register_routes(app):

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
        end = time.time()
        print(end-start)
        return render_template('index.html')
    
    @app.route('/graph')
    def graph():
        return render_template('graph.html')
    
    @app.route('/literature')
    def literature():
        return render_template('literature.html')