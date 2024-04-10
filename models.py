from db import db


class Links(db.Model):
    __tablename__ = "links"
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.Text(), unique=True, nullable=False)
    description = db.Column(db.Text())
    article_title = db.Column(db.Text())
    image = db.Column(db.Text())
    date = db.Column(db.String(30))
    authors = db.relationship('Authors', backref='author', lazy=True)
    keywords = db.relationship('Keywords', backref='keyword', lazy=True)
    citations = db.relationship('Citations', backref='citation', lazy=True)

    def __repr__(self):
        return f'Link: {self.link}'


class Keywords(db.Model):
    _tablename__ = "keywords"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id'))
    word = db.Column(db.Text())

    def __repr__(self):
        return f'Keyword: {self.word}'


class Citations(db.Model):
    _tablename__ = "citations"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id'))
    reference = db.Column(db.Text())

    def __repr__(self):
        return f'Citation: {self.reference}'


class Authors(db.Model):
    _tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id'))
    name = db.Column(db.Text())

    def __repr__(self):
        return f'Author: {self.name}'
