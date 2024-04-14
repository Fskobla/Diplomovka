from . import db


class Links(db.Model):
    __tablename__ = "links"
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.Text(), unique=True, nullable=False)
    word = db.Column(db.String(30))
    description = db.Column(db.Text())
    article_title = db.Column(db.Text())
    image = db.Column(db.Text())
    date = db.Column(db.String(30))
    authors = db.relationship('Authors', backref='author', lazy=True)
    keywords = db.relationship('Keywords', backref='keyword', lazy=True)
    citations = db.relationship('Citations', backref='citation', lazy=True)

    def __repr__(self):
        return f'Link: {self.link}'

    def to_dict(self):
        return {
            'id': self.id,
            'link': self.link,
            'word': self.word,
            'description': self.description,
            'article_title': self.article_title,
            'image': self.image,
            'date': self.date,
            'authors': [author.to_dict() for author in self.authors],
            'keywords': [keyword.to_dict() for keyword in self.keywords],
            'citations': [citation.to_dict() for citation in self.citations]
        }


class Keywords(db.Model):
    __tablename__ = "keywords"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id'))
    word = db.Column(db.Text())

    def __repr__(self):
        return f'Keyword: {self.word}'

    def to_dict(self):
        return {
            'id': self.id,
            'link_id': self.link_id,
            'word': self.word
        }


class Citations(db.Model):
    __tablename__ = "citations"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id'))
    reference = db.Column(db.Text())

    def __repr__(self):
        return f'Citation: {self.reference}'

    def to_dict(self):
        return {
            'id': self.id,
            'link_id': self.link_id,
            'reference': self.reference
        }


class Authors(db.Model):
    __tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('links.id'))
    name = db.Column(db.Text())

    def __repr__(self):
        return f'Author: {self.name}'

    def to_dict(self):
        return {
            'id': self.id,
            'link_id': self.link_id,
            'name': self.name
        }
