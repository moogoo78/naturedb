"""Species tab: /species (tree), /api/species-tree/children, /species/<id>.

Run against the dev DB with the HAST site (setting frontend.species; tree from collection_taxon_map).
"""
import json

import pytest

HAST = {'Host': 'hast.localhost'}


@pytest.fixture()
def hast(app):
    with app.app_context():
        from app.models.site import Site
        site = Site.query.filter(Site.name == 'hast').first()
        if not site or not site.get_settings('frontend.species'):
            pytest.skip('hast has no frontend.species setting')
        from app.helpers import site_taxon_tree_ids
        tree_ids = site_taxon_tree_ids(site)
        if len(tree_ids) != 1:
            pytest.skip(f'hast maps to taxon trees {tree_ids}, need exactly one')
        yield site, tree_ids[0]


def _roots(client):
    r = client.get('/api/species-tree/children', headers=HAST)
    assert r.status_code == 200
    return r.get_json()


def _family_with_children(client):
    fam = next((n for n in _roots(client) if n['rank'] == 'family' and n['has_children']), None)
    if not fam:
        pytest.skip('no family with children')
    return fam


def _search_total(client, taxon_id):
    r = client.get('/api/v1/search', headers=HAST, query_string={
        'filter': json.dumps({'taxon_id': taxon_id}), 'range': '[0,1]'})
    return r.get_json()['total']


class TestSpeciesIndex:
    def test_page_and_nav_tab(self, client, hast):
        r = client.get('/species', headers=HAST)
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert 'id="species-tree"' in html
        assert 'href="/species"' in html  # nav tab

    def test_roots_are_counted_and_families_first(self, client, hast):
        roots = _roots(client)
        assert roots and all(n['count'] > 0 for n in roots)
        ranks = [n['rank'] for n in roots]
        assert ranks[0] == 'family'
        assert ranks == sorted(ranks, key=lambda r: r != 'family')  # orphans after families

    def test_family_total_is_own_plus_children(self, client, hast):
        from app.helpers import get_taxon_unit_counts
        site, tree_id = hast
        fam = _family_with_children(client)
        kids = client.get(f'/api/species-tree/children?parent_id={fam["id"]}', headers=HAST).get_json()
        assert kids and all(k['count'] > 0 for k in kids)
        _, direct = get_taxon_unit_counts(site, tree_id)
        assert fam['count'] == direct.get(fam['id'], 0) + sum(k['count'] for k in kids)


class TestSpeciesDetail:
    def test_count_equals_search_total(self, client, hast):
        fam = _family_with_children(client)
        html = client.get(f'/species/{fam["id"]}', headers=HAST).get_data(as_text=True)
        assert f'href="/data?taxon={fam["id"]}"' in html
        assert f'{fam["count"]:,}' in html
        assert fam['count'] == _search_total(client, fam['id'])

    def test_species_page(self, client, hast):
        fam = _family_with_children(client)
        node, parent = fam, None
        while node['has_children']:  # walk down to a leaf
            parent = node
            node = client.get(f'/api/species-tree/children?parent_id={node["id"]}',
                              headers=HAST).get_json()[0]
        r = client.get(f'/species/{node["id"]}', headers=HAST)
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert 'aria-label="分類位置"' in html  # sidebar
        assert 'aria-current="page"' in html
        assert node['name'].split()[0] in html
        assert f'href="/species/{parent["id"]}"' in html  # ancestor row is linked
        assert f'href="/species/{node["id"]}"' not in html  # current row is not

    def test_sidebar_lists_siblings(self, client, hast):
        fam = _family_with_children(client)
        kids = client.get(f'/api/species-tree/children?parent_id={fam["id"]}', headers=HAST).get_json()
        if len(kids) < 2:
            pytest.skip('family has a single child')
        html = client.get(f'/species/{kids[0]["id"]}', headers=HAST).get_data(as_text=True)
        assert all(f'href="/species/{k["id"]}"' in html for k in kids[1:])

    def test_synonym_match_shows_taicol_note(self, client, hast):
        from app.models.taxon import Taxon
        site, tree_id = hast
        t = Taxon.query.filter(Taxon.tree_id == tree_id,
                               Taxon.full_scientific_name.like('Gordonia axillaris%')).first()
        if not t or not site.get_settings('frontend.taxon.reference'):
            pytest.skip('needs Gordonia axillaris and the TaiCOL reference setting')
        html = client.get(f'/species/{t.id}', headers=HAST).get_data(as_text=True)
        assert '依異名對照' in html

    def test_unknown_and_foreign_taxa_are_404(self, client, hast):
        from app.models.taxon import Taxon
        _, tree_id = hast
        assert client.get('/species/0', headers=HAST).status_code == 404
        other = Taxon.query.filter(Taxon.tree_id != tree_id).first()
        if other:
            assert client.get(f'/species/{other.id}', headers=HAST).status_code == 404


class TestOptIn:
    def test_site_without_setting_has_no_tab(self, app, client):
        with app.app_context():
            from app.models.site import Site
            site = next((s for s in Site.query.all()
                         if s.name != 'hast' and not s.get_settings('frontend.species')), None)
        if not site:
            pytest.skip('no other site')
        host = {'Host': f'{site.name}.localhost'}
        assert client.get('/species', headers=host).status_code == 404
        assert client.get('/api/species-tree/children', headers=host).status_code == 404
        home = client.get('/', headers=host)
        if home.status_code == 200:
            assert 'href="/species"' not in home.get_data(as_text=True)


class TestTreeFromCollectionMap:
    def test_hast_tree_comes_from_collection_taxon_map(self, app, hast):
        from app.models.collection import CollectionTaxonMap
        site, tree_id = hast
        maps = CollectionTaxonMap.query.filter(
            CollectionTaxonMap.collection_id.in_([c.id for c in site.collections])).all()
        assert {m.taxon_tree_id for m in maps} == {tree_id}

    def test_opted_in_site_without_single_tree_is_404(self, app, client, monkeypatch):
        import app.blueprints.frontpage as fp
        from app.models.site import Site
        with app.app_context():
            hast = Site.query.filter(Site.name == 'hast').first()
        if not hast or not hast.get_settings('frontend.species'):
            pytest.skip('hast has no frontend.species setting')
        for trees in ([], [1, 2]):
            monkeypatch.setattr(fp, 'site_taxon_tree_ids', lambda site, t=trees: t)
            assert client.get('/species', headers=HAST).status_code == 404
