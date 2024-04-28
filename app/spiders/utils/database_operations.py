# Function for removing data in Links table
from app.models import Citations, Links, link_authors, link_keywords, Authors, Keywords, BadLinks


def remove_links_from_database(database, word):
    # Get all links IDs associated with the given word
    link_ids = [row[0] for row in database.session.query(Links.id).filter(Links.word == word).all()]

    # Delete all citations associated with the link
    Citations.query.filter(Citations.link_id.in_(link_ids)).delete(synchronize_session=False)

    # Delete the records from the link_authors table
    database.session.query(link_authors).filter(link_authors.c.link_id.in_(link_ids)).delete(synchronize_session=False)
    database.session.query(link_keywords).filter(link_keywords.c.link_id.in_(link_ids)).delete(synchronize_session=False)

    # Delete all authors associated with the link
    Authors.query.filter(Authors.link_id.in_(link_ids)).delete(synchronize_session=False)

    # Delete all keywords associated with the links
    Keywords.query.filter(Keywords.link_id.in_(link_ids)).delete(synchronize_session=False)

    # Delete the links based on the word
    Links.query.filter(Links.word == word).delete()

    # Commit the changes
    database.session.commit()


# Function for removing data in BadLinks table
def remove_bad_links_from_database(database, word):
    bad_link_in_database = BadLinks.query.filter_by(word=word).all()
    if len(bad_link_in_database) != 0:
        for link in bad_link_in_database:
            database.session.delete(link)
        database.session.commit()