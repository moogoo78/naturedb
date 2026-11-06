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
