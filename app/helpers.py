
from app.models.site import Organization
from app.models.collection import (
    Collection,
    Unit
)

def get_current_site(request):
    if request and request.headers:
        if domain := request.headers.get('Host'):
            if site := Organization.get_site(domain):
                return site
    return None
