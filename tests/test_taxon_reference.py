import pytest

from app.models.taxon import parse_scientific_name


class TestParseScientificName:
    def test_binomial_with_author(self):
        assert parse_scientific_name('Floscopa scandens Lour.') == \
            ('Floscopa scandens', 'Floscopa scandens', 'Lour.')

    def test_variety_keeps_deepest_part_and_its_author(self):
        assert parse_scientific_name('Acer mono var. glabrum (H. Lév. & Vaniot) H. Hara') == \
            ('Acer mono var. glabrum', 'Acer mono', '(H. Lév. & Vaniot) H. Hara')

    def test_author_f_is_not_forma(self):
        # "(Burm. f.)" is an author abbreviation, not a forma marker
        canonical, binomial, author = parse_scientific_name(
            'Vandellia anagallis (Burm. f.) Yamazaki var. anagallis')
        assert canonical == 'Vandellia anagallis var. anagallis'
        assert binomial == 'Vandellia anagallis'

    def test_forma_normalised_to_fo(self):
        assert parse_scientific_name('Adiantum capillus-veneris f. lanyuanum W.C.Shieh')[0] == \
            'Adiantum capillus-veneris fo. lanyuanum'

    def test_ssp_normalised_to_subsp(self):
        assert parse_scientific_name('Celastrus paniculatus Willd. ssp. multiflorus (Roxb.) Hou')[0] == \
            'Celastrus paniculatus subsp. multiflorus'

    def test_hybrid_sign(self):
        assert parse_scientific_name('Abelia × grandiflora (Rovelli ex André) Rehder')[0] == \
            'Abelia × grandiflora'

    def test_hybrid_sign_glued_to_epithet(self):
        assert parse_scientific_name('Begonia ×taipeiensis C.I Peng') == \
            ('Begonia × taipeiensis', 'Begonia × taipeiensis', 'C.I Peng')

    @pytest.mark.parametrize('name', ['', None, 'Begonia', 'Begonia sect. Alicida', 'ASPLENIACEAE'])
    def test_non_species_names(self, name):
        assert parse_scientific_name(name) == (None, None, '')


@pytest.fixture()
def taicol(app):
    with app.app_context():
        from app.models.taxon import Taxon, TaxonTree
        tree = TaxonTree.query.filter(TaxonTree.is_external == True).first()
        legacy = TaxonTree.query.filter(TaxonTree.is_external.isnot(True)).first()
        if not tree or not legacy:
            pytest.skip('needs an external and an internal taxon tree loaded')
        yield tree, legacy, Taxon


def _legacy(Taxon, legacy, name):
    t = Taxon.query.filter(Taxon.tree_id == legacy.id,
                           Taxon.full_scientific_name == name).first()
    if not t:
        pytest.skip(f'{name} not in {legacy.name}')
    return t


class TestFindReferenceMatch:
    def test_exact_species(self, taicol):
        tree, legacy, Taxon = taicol
        ref, match = _legacy(Taxon, legacy, 'Asplenium nidus L.').find_reference_match(tree.id)
        assert match == 'exact'
        assert ref.tree_id == tree.id
        assert ref.canonical_name == 'Asplenium nidus'

    def test_uppercase_family(self, taicol):
        tree, legacy, Taxon = taicol
        ref, match = _legacy(Taxon, legacy, 'ASPLENIACEAE').find_reference_match(tree.id)
        assert (match, ref.rank, ref.canonical_name) == ('name', 'family', 'Aspleniaceae')

    def test_same_tree_is_direct(self, taicol):
        tree, _, Taxon = taicol
        t = Taxon.query.filter(Taxon.tree_id == tree.id, Taxon.rank == 'species').first()
        assert t.find_reference_match(tree.id) == (t, 'direct')

    def test_no_tree(self, taicol):
        _, legacy, Taxon = taicol
        assert _legacy(Taxon, legacy, 'Asplenium nidus L.').find_reference_match(None) == (None, '')


class TestTaxonReferenceHelper:
    def test_orphan_variety_borrows_species_lineage(self, taicol):
        from app.helpers import get_taxon_reference
        tree, legacy, Taxon = taicol
        t = _legacy(Taxon, legacy, 'Justicia procumbens L. var. procumbens')
        ref = get_taxon_reference(t, {'tree_id': tree.id})
        ranks = [x['rank'] for x in ref['lineage']]
        assert ranks[0] == 'kingdom'
        assert ranks[-2:] == ['species', 'variety']
        assert '|' not in ref['common']

    def test_missing_setting(self, taicol):
        from app.helpers import get_taxon_reference
        _, legacy, Taxon = taicol
        assert get_taxon_reference(_legacy(Taxon, legacy, 'Asplenium nidus L.'), {}) is None


class TestSynonymIndex:
    def test_synonym_resolves_to_accepted(self, taicol):
        tree, legacy, Taxon = taicol
        t = _legacy(Taxon, legacy, 'Gordonia axillaris (Roxb. ex Ker Gawl.) D. Dietr.')
        assert Taxon.find_reference_matches([t], tree.id)[t.id] == (None, '')
        syn = Taxon.build_synonym_index(tree.id, ['Plantae'])
        ref, match = Taxon.find_reference_matches([t], tree.id, synonyms=syn)[t.id]
        assert match == 'synonym'
        assert ref.canonical_name == 'Polyspora axillaris'

    def test_kingdom_filter_drops_cross_kingdom_synonyms(self, taicol):
        # "Thea" (tea) is also a synonym of the ladybird genus Psyllobora
        tree, _, Taxon = taicol
        everything = Taxon.build_synonym_index(tree.id)
        if 'Thea' not in everything:
            pytest.skip('Thea not a synonym in this TaiCOL release')
        plants = Taxon.build_synonym_index(tree.id, ['Plantae'])
        assert all(r.source_data.get('kingdom') == 'Plantae' for r in plants.values())
        assert plants.get('Thea') is None or plants['Thea'].source_data['kingdom'] == 'Plantae'


class TestStoredReferenceMatch:
    '''taxon_reference_match rows; every test rolls back.'''

    @pytest.fixture()
    def stored(self, taicol):
        from app.database import session
        from app.models.taxon import TaxonReferenceMatch
        tree, legacy, Taxon = taicol
        t = _legacy(Taxon, legacy, 'Asplenium nidus L.')
        TaxonReferenceMatch.query.filter_by(taxon_id=t.id, tree_id=tree.id).delete()
        yield tree, t, Taxon, TaxonReferenceMatch
        session.rollback()

    def test_missing_row_falls_back_to_live_match(self, stored):
        tree, t, Taxon, _ = stored
        ref, match = Taxon.get_reference_matches([t], tree.id)[t.id]
        assert (match, ref.canonical_name) == ('exact', 'Asplenium nidus')

    def test_stored_row_wins(self, stored):
        tree, t, Taxon, M = stored
        other = Taxon.query.filter(Taxon.tree_id == tree.id, Taxon.rank == 'species',
                                   Taxon.canonical_name != 'Asplenium nidus').first()
        M.upsert([{'taxon_id': t.id, 'tree_id': tree.id, 'ref_taxon_id': other.id,
                   'match_type': 'manual'}])
        assert Taxon.get_reference_matches([t], tree.id)[t.id] == (other, 'manual')

    def test_stored_no_match_is_no_match(self, stored):
        tree, t, Taxon, M = stored
        M.upsert([{'taxon_id': t.id, 'tree_id': tree.id, 'ref_taxon_id': None,
                   'match_type': 'none'}])
        assert Taxon.get_reference_matches([t], tree.id)[t.id] == (None, '')

    def test_upsert_never_overwrites_manual(self, stored):
        from app.database import session
        tree, t, Taxon, M = stored
        other = Taxon.query.filter(Taxon.tree_id == tree.id, Taxon.rank == 'species',
                                   Taxon.canonical_name != 'Asplenium nidus').first()
        session.add(M(taxon_id=t.id, tree_id=tree.id, ref_taxon_id=other.id,
                      match_type='manual', is_manual=True))
        session.flush()
        live, _ = Taxon.find_reference_matches([t], tree.id)[t.id]
        M.upsert([{'taxon_id': t.id, 'tree_id': tree.id, 'ref_taxon_id': live.id,
                   'match_type': 'exact'}])
        session.expire_all()
        row = M.query.filter_by(taxon_id=t.id, tree_id=tree.id).one()
        assert (row.ref_taxon_id, row.match_type, row.is_manual) == (other.id, 'manual', True)

    def test_reference_tree_taxon_is_direct(self, stored):
        tree, _, Taxon, _ = stored
        t = Taxon.query.filter(Taxon.tree_id == tree.id, Taxon.rank == 'species').first()
        assert Taxon.get_reference_matches([t], tree.id)[t.id] == (t, 'direct')
