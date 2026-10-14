"""Optional `section` rank: taxon_relation.depth is a path length, so a section
between genus and species shifts depths, and lookups must go by Taxon.rank.

Runs against the dev DB: builds throwaway taxa (no tree) and removes it afterwards.
"""
import json

import pytest

from app.database import session
from app.models.taxon import Taxon, TaxonRelation
from app.models.collection import Record


def _depths(taxon):
    rels = TaxonRelation.query.filter(TaxonRelation.child_id==taxon.id, TaxonRelation.depth > 0).all()
    return {r.parent.rank: r.depth for r in rels}


@pytest.fixture()
def tree(app):
    with app.app_context():
        taxa = {}
        for rank, name in [('family', 'Pytestaceae'), ('genus', 'Pytestia'),
                           ('section', 'Pytestia sect. Alpha'), ('species', 'Pytestia beta'),
                           ('species', 'Pytestia gamma')]:
            t = Taxon(rank=rank, full_scientific_name=name)
            session.add(t)
            taxa[name] = t
        session.commit()
        fam, gen, sec = taxa['Pytestaceae'], taxa['Pytestia'], taxa['Pytestia sect. Alpha']
        fam.make_relations({})
        gen.make_relations({'family': fam.id})
        sec.make_relations({'family': fam.id, 'genus': gen.id})
        taxa['Pytestia beta'].make_relations({'family': fam.id, 'genus': gen.id, 'section': sec.id})
        taxa['Pytestia gamma'].make_relations({'family': fam.id, 'genus': gen.id})

        yield taxa

        ids = [t.id for t in taxa.values()]
        Record.query.filter(Record.proxy_taxon_id.in_(ids)).delete(synchronize_session=False)
        TaxonRelation.query.filter(TaxonRelation.child_id.in_(ids)).delete(synchronize_session=False)
        Taxon.query.filter(Taxon.id.in_(ids)).delete(synchronize_session=False)
        session.commit()


def test_depth_is_path_length(tree):
    assert _depths(tree['Pytestia beta']) == {'section': 1, 'genus': 2, 'family': 3}
    assert _depths(tree['Pytestia gamma']) == {'genus': 1, 'family': 2}
    assert _depths(tree['Pytestia sect. Alpha']) == {'genus': 1, 'family': 2}


def test_unsubmitted_section_is_kept(tree):
    # the admin form only sends family/genus
    sp = tree['Pytestia beta']
    sp.make_relations({'family': tree['Pytestaceae'].id, 'genus': tree['Pytestia'].id})
    assert _depths(sp) == {'section': 1, 'genus': 2, 'family': 3}


def test_removing_section_shrinks_depths(tree):
    sp = tree['Pytestia beta']
    sp.make_relations({'section': None})
    assert _depths(sp) == {'genus': 1, 'family': 2}


def test_higher_taxon_by_rank(tree):
    sp = tree['Pytestia beta']
    assert sp.get_higher_taxon('family').id == tree['Pytestaceae'].id
    assert sp.get_higher_taxon('section').id == tree['Pytestia sect. Alpha'].id


def test_record_taxon_family_under_section(tree):
    for name in ('Pytestia beta', 'Pytestia gamma'):
        rec = Record(proxy_taxon_id=tree[name].id)
        session.add(rec)
        session.commit()
        session.refresh(rec)
        assert rec.taxon_family.id == tree['Pytestaceae'].id


def test_siblings_include_species_across_sections(tree):
    # parent is the genus: every species of the genus, sections or not (never the section itself)
    names = {t.full_scientific_name for t in tree['Pytestia gamma'].get_siblings()}
    assert names == {'Pytestia beta', 'Pytestia gamma'}
    # parent is the section: only species of that section
    names = {t.full_scientific_name for t in tree['Pytestia beta'].get_siblings()}
    assert names == {'Pytestia beta'}


def test_api_species_of_genus_include_sectioned(client, tree):
    filtr = {'rank': 'species', 'parent_id': tree['Pytestia'].id}
    resp = client.get(f'/api/v1/taxa?filter={json.dumps(filtr)}&range=[-1,-1]')
    assert resp.status_code == 200
    names = {x['full_scientific_name'] for x in resp.get_json()['data']}
    assert names == {'Pytestia beta', 'Pytestia gamma'}


def _tree_children(client, **params):
    resp = client.get('/api/taxon-tree/children', query_string={'tree_id': 1, **params},
                      headers={'Host': 'hast.sh21.ml:5000'})
    assert resp.status_code == 200
    return {x['name']: x['rank'] for x in resp.get_json()}


def test_tree_children_direct(client, tree):
    # no rank: direct children only, the section is listed but not its species
    assert _tree_children(client, parent_id=tree['Pytestia'].id) == {
        'Pytestia sect. Alpha': 'section', 'Pytestia gamma': 'species'}


def test_tree_children_rank_any_depth(client, tree):
    assert _tree_children(client, parent_id=tree['Pytestia'].id, rank='species') == {
        'Pytestia beta': 'species', 'Pytestia gamma': 'species'}
    assert _tree_children(client, parent_id=tree['Pytestaceae'].id, rank='section,species') == {
        'Pytestia sect. Alpha': 'section', 'Pytestia beta': 'species', 'Pytestia gamma': 'species'}
