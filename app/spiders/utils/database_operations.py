# Function for removing data in Links table
from app.models import Citations, Links, link_authors, link_keywords, Authors, Keywords, BadLinks


def remove_links_from_database(database, word):
    # Get all links associated with the given word
    links = Links.query.filter_by(word=word).all()

    for link in links:
        # Clear all keywords associated with the link
        link.keywords.clear()

        # Delete all citations associated with the link
        Citations.query.filter_by(link_id=link.id).delete(synchronize_session=False)

        # Delete all authors associated with the link
        link.authors.clear()

        # Commit the changes to clear the session
        database.session.commit()

        # Delete the link itself
        database.session.delete(link)

    # Commit the changes outside the loop
    database.session.commit()

# Function for removing data in BadLinks table
def remove_bad_links_from_database(database, word):
    bad_links = BadLinks.query.filter_by(word=word).all()

    for bad_link in bad_links:
        database.session.delete(bad_link)

    database.session.commit()