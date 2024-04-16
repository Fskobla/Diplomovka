from flask import render_template, request, redirect, url_for, jsonify, abort
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
        return render_template('graph.html')

    @app.route('/literature', methods=['GET','POST'])
    def literature():
        word = request.args.get('word')
        if word:
            links = Links.query.filter_by(word=word).all()
        else:
            abort(404)
        return render_template('literature.html', links=links)
