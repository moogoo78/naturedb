from flask import (
    Blueprint,
    render_template,
)
import markdown

from app.database import session
from app.models.site import (
    Organization,
    Article,
)
from app.models.collection import (
    Unit,
)

page = Blueprint('page', __name__)

@page.route('/people')
def people():
    return render_template('page-people.html')

@page.route('/visiting')
def visiting():
    return render_template('page-visiting.html')

@page.route('/making-specimen')
def making_specimen():
    return render_template('page-making-specimen.html')

@page.route('/about')
def about_page():
    return render_template('page-about.html')

@page.route('/type_specimens')
def type_specimens():
    units = Unit.query.filter(Unit.type_status != '').all()
    return render_template('page-type-specimens.html', units=units)

@page.route('/related_links')
def related_links():
    org = session.get(Organization, 1)
    return render_template('related_links.html', organization=org)

@page.route('/articles/<article_id>')
def article_detail(article_id):
    article = Article.query.get(article_id)
    article.content_html = markdown.markdown(article.content)
    return render_template('article-detail.html', article=article)
