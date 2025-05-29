import json
from pathlib import Path

from app import create_app


#def test_config():
#    assert not create_app().testing
#    assert create_app().testing


def test_ping(client):
    response = client.get('/ping')
    assert response.status_code == 200

def test_settings():
    p = Path('/code/app/settings')
    for f in p.iterdir():
        if f.suffix == '.json':
            # json format
            json_file = open(Path(p, f))
            json_data = json.loads(json_file.read())
