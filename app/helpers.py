
from app.models.site import Organization
from app.models.collection import (
    Collection,
    Unit
)

def get_current_site(request):
    if request and request.headers:
        if domain := request.headers.get('Host'):
            if site := Organization.query.filter(Organization.is_site==True, Organization.domain==domain).first():
                return site
    return None
