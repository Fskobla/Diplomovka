from . import db


class Links(db.Model):
    __tablename__ = "links"
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.Text(), unique=True, nullable=False)
    word = db.Column(db.String(30))
    description = db.Column(db.Text())
    article_title = db.Column(db.Text())
    image = db.Column(db.Text())
    source = db.Column(db.String(20))
    date = db.Column(db.String(30))
    authors = db.relationship('Authors', secondary='link_authors', lazy=True, backref=db.backref('link', lazy=True))
    keywords = db.relationship('Keywords', secondary='link_keywords', lazy=True, backref=db.backref('link', lazy=True))
    citations = db.relationship('Citations', backref='link', lazy=True)

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
            'source': self.source,
            'date': self.date,
            'authors': [author.to_dict() for author in self.authors],
            'keywords': [keyword.to_dict() for keyword in self.keywords],
            'citations': [citation.to_dict() for citation in self.citations]
        }


link_authors = db.Table('link_authors',
                        db.Column('link_id', db.Integer, db.ForeignKey('links.id'), primary_key=True),
                        db.Column('author_id', db.Integer, db.ForeignKey('authors.id'), primary_key=True)
                        )

link_keywords = db.Table('link_keywords',
                         db.Column('link_id', db.Integer, db.ForeignKey('links.id'), primary_key=True),
                         db.Column('keyword_id', db.Integer, db.ForeignKey('keywords.id'), primary_key=True)
                         )


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


class BadLinks(db.Model):
    __tablename__ = "bad_links"
    id = db.Column(db.Integer, primary_key=True)
    bad_link = db.Column(db.Text(), nullable=False)
    source = db.Column(db.String(20))
    word = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.Text())


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
