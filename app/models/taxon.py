import re

from flask_babel import (
    get_locale,
    gettext,
)

from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Table,
    Index,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import (
    Base,
    session
)

# rank markers normalised to TaiCOL canonical style ("fo." not "f.")
RANK_MARKERS = {
    'var.': 'var.', 'var': 'var.',
    'subsp.': 'subsp.', 'ssp.': 'subsp.', 'subsp': 'subsp.',
    'f.': 'fo.', 'fo.': 'fo.', 'forma': 'fo.',
}
_EPITHET_RE = re.compile(r'^[a-z][a-z\-]+$')
_HYBRID_SIGNS = ('×', 'x', 'X')


def parse_scientific_name(full):
    '''Split a full name with inline authors into its parts.

    'Acer mono var. glabrum (H. Lév.) H. Hara'
        -> ('Acer mono var. glabrum', 'Acer mono', '(H. Lév.) H. Hara')

    Returns (canonical, binomial, author); (None, None, '') when the name is
    not a species-level binomial. Only the deepest infraspecific part is kept,
    and "f." is an author abbreviation unless followed by a lowercase epithet
    ("L. f. var. x" -> var. x).
    '''
    toks = (full or '').split()
    # "Begonia ×taipeiensis": hybrid sign glued to the epithet
    if len(toks) >= 2 and toks[1].startswith('×') and len(toks[1]) > 1:
        toks[1:2] = ['×', toks[1][1:]]
    if len(toks) < 2:
        return None, None, ''
    i = 1
    hybrid = ''
    if toks[i] in _HYBRID_SIGNS and len(toks) > 2:
        hybrid = '× '
        i += 1
    if not _EPITHET_RE.match(toks[i]):
        return None, None, ''
    binomial = f'{toks[0]} {hybrid}{toks[i]}'
    canonical = binomial
    author_start = i + 1
    j = i + 1
    while j < len(toks) - 1:
        marker = RANK_MARKERS.get(toks[j])
        nxt = toks[j + 1]
        if marker and _EPITHET_RE.match(nxt) and nxt not in RANK_MARKERS:
            canonical = f'{canonical} {marker} {nxt}'
            author_start = j + 2
            j += 2
        else:
            j += 1
    return canonical, binomial, ' '.join(toks[author_start:])


def _norm_author(s):
    return re.sub(r'\s+', '', s or '').lower()


class TaxonTree(Base):

    __tablename__ = 'taxon_tree'
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))
    memo = Column(String(1000))
    # ordered rank list for this tree, e.g. ["kingdom","phylum","class","order","family","genus","species"]
    hierarchy = Column(JSONB)
    is_external = Column(Boolean, default=False)  # external checklist (e.g., TaiCOL) vs internal/legacy

class TaxonRelation(Base):
    '''closure table
    '''
    __tablename__ = 'taxon_relation'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('taxon.id', ondelete='SET NULL'), index=True)
    child_id = Column(Integer, ForeignKey('taxon.id', ondelete='SET NULL'), index=True)
    depth = Column(SmallInteger)
    parent = relationship('Taxon', foreign_keys='TaxonRelation.parent_id')
    child = relationship('Taxon', foreign_keys='TaxonRelation.child_id')

    def __repr__(self):
        return f'<TaxonRelation parent={self.parent} child={self.child}>'


class TaxonProvider(Base):
    __tablename__ = 'taxon_provider'
    id = Column(Integer, primary_key=True)
    name = Column(String(500))


class Taxon(Base):
    '''abcd: TaxonIdentified
    '''
    # taxon_relation.depth is the path length in the closure table, so an
    # optional rank (e.g. Begonia sections) shifts the depth of everything
    # below it: never infer a rank from a depth number, compare Taxon.rank.
    RANK_HIERARCHY = ['family', 'genus', 'section', 'species']
    RANK_OPTIONAL = ('section',)
    RANK_HIERARCHY_MAJOR = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']

    # used in name string
    RANK_ABBR = [
        'subgen.',
        'sect.',
        'subsp.',
        'var.',
        'subvar.',
        'forma',
        'f.',
        'subforma',
        'subf.',
        'f.spec.'
    ]
    __tablename__ = 'taxon'
    __table_args__ = (
        # name lookup within one tree (reference-tree matching on public pages)
        Index('ix_taxon_tree_id_canonical_name', 'tree_id', 'canonical_name'),
    )
    id = Column(Integer, primary_key=True)
    rank = Column(String(50), index=True)
    full_scientific_name = Column(String(500), index=True)
    # Botanical
    specific_epithet = Column(String(500)) # first specific
    infraspecific_epithet = Column(String(500))
    infraspecific_epithet2 = Column(String(500)) # final epithet
    rank_abbr = Column(String(500))
    author = Column(String(500))
    #author_parenthesis = Column(String(500))
    canonical_name = Column(String(500))
    #canonical_name_full = Column(String(500))
    # status = Column(String(50))

    #dwc.taxonomicStatus: invalid, misapplied, homotypic synonym, accepted
    #dwc.nomenclaturalStatus: nom. ambig., nom. illeg., nom. subnud.

    common_name = Column(String(500)) # abcd: InformalName
    code = Column(String(500))
    tree_id = Column(ForeignKey('taxon_tree.id', ondelete='SET NULL'))
    tree = relationship('TaxonTree')
    #provider_source_id =
    #provider_id = Column(Integer, ForeignKey('taxon_provider.id', ondelete='SET NULL'))
    #provider_source_id = Column(String(500))
    is_accepted = Column(Boolean, default=True)
    #hybrid_flag =
    #author_team_parenthesis
    #author_team
    #cultivar_group_name
    #cultivar_ame
    #trade_designation_names


    # abcd: Zoological
    #Subgenus
    #SubspeciesEpithet
    #Breed
    source_id = Column(String(500))  # external checklist ID (e.g. TaiCOL taxon_id)
    source_data = Column(JSONB)

    def __repr__(self):
        return f'<Taxon id="{self.id}" name="{self.full_scientific_name}/{self.common_name}">'

    @property
    def display_name(self):
        s = self.full_scientific_name
        if x := self.common_name:
            s = f'{s} ({x})'
        return s

    @property
    def display_verbose_name(self):
        taxon_family = ''
        if self.rank != 'family':
            if family := self.get_higher_taxon('family'):
                taxon_family = family.full_scientific_name
                if cn := family.common_name:
                    taxon_family = '{} ({})'.format(taxon_family, cn)

        s = '[{}] {} / {}'.format(self.rank, taxon_family, self.full_scientific_name)
        if self.common_name:
            s = '{} ({})'.format(s, self.common_name)
        return s

    @property
    def rank_depth(self):
        return self.RANK_HIERARCHY.index(self.rank)

    def get_parents(self):
        res = TaxonRelation.query.filter(TaxonRelation.child_id==self.id, TaxonRelation.parent_id!=self.id).order_by(desc(TaxonRelation.depth)).all()
        return [x.parent for x in res]

    def get_children(self, depth=0):
        if depth:
            res = TaxonRelation.query.filter(TaxonRelation.parent_id==self.id, TaxonRelation.depth==depth).all()
        else:
            res = TaxonRelation.query.filter(TaxonRelation.parent_id==self.id).order_by(TaxonRelation.depth).all()
        return [x.child for x in res if x.child is not None]

    def descendant_ids_subquery(self):
        '''ids of all descendants at any depth, excluding self'''
        return session.query(TaxonRelation.child_id).filter(
            TaxonRelation.parent_id==self.id,
            TaxonRelation.depth > 0,
        )

    def get_descendants(self, rank):
        '''all descendants of a given rank, at any depth (skips optional ranks in between)'''
        res = Taxon.query.join(TaxonRelation, TaxonRelation.child_id==Taxon.id).filter(
            TaxonRelation.parent_id==self.id,
            TaxonRelation.depth > 0,
            Taxon.rank==rank,
        ).all()
        return res

    def get_siblings(self):
        if self.rank_depth == 0:
            taxa = Taxon.query.filter(Taxon.rank==Taxon.RANK_HIERARCHY[0]).order_by(Taxon.full_scientific_name).all()
            return taxa
        else:
            if tr := TaxonRelation.query.filter(TaxonRelation.child_id==self.id, TaxonRelation.depth==1).first():
                return tr.parent.get_descendants(self.rank)
        return []

    def find_reference_match(self, tree_id, prefer_kingdoms=None):
        '''Find this taxon by name in another (reference) tree.

        Returns (taxon, match_type); match_type is one of
        direct (already in that tree), exact (name + author), canonical
        (name only), autonym ("X y var. y" -> "X y"), name (family/genus/...),
        or (None, '') when nothing matches. Synonyms are not resolved: the
        reference tree holds accepted names only.

        prefer_kingdoms breaks ties between homonyms (e.g. a plant and an
        animal genus of the same name) when this taxon's own tree has no
        kingdom rank.
        '''
        if not tree_id:
            return None, ''
        if self.tree_id == tree_id:
            return self, 'direct'

        base = Taxon.query.filter(Taxon.tree_id == tree_id)
        if self.rank in ('species', 'subspecies', 'variety', 'form'):
            canonical, binomial, author = parse_scientific_name(self.full_scientific_name)
            if self.canonical_name:
                canonical = self.canonical_name
                author = self.author or author
            if not canonical:
                return None, ''
            cands = base.filter(Taxon.canonical_name == canonical).all()
            match_type = 'canonical'
            if not cands and binomial and canonical != binomial \
               and canonical.split()[-1] == binomial.split()[-1]:
                cands = base.filter(Taxon.canonical_name == binomial).all()
                match_type = 'autonym'
            if not cands:
                return None, ''
            if author and (exact := [c for c in cands
                                     if _norm_author(c.author) == _norm_author(author)]):
                cands = exact
                if match_type == 'canonical':
                    match_type = 'exact'
        else:
            name = (self.canonical_name or self.full_scientific_name or '').strip()
            if name.isupper():  # legacy upper-case family names
                name = name.capitalize()
            if not name:
                return None, ''
            cands = base.filter(Taxon.canonical_name == name, Taxon.rank == self.rank).all()
            match_type = 'name'
            if not cands:
                return None, ''

        if len(cands) > 1:
            if mine := self.get_higher_taxon('kingdom'):
                kingdoms = [mine.full_scientific_name]
            else:
                kingdoms = prefer_kingdoms or []
            def score(c):
                k = c.get_higher_taxon('kingdom')
                preferred = bool(k and k.full_scientific_name in kingdoms)
                return (not preferred, not c.is_accepted, c.id)
            cands.sort(key=score)
        return cands[0], match_type

    @classmethod
    def find_reference_matches(cls, taxa, tree_id, prefer_kingdoms=None, synonyms=None):
        '''Batched find_reference_match: {taxon.id: (ref|None, match_type)}.

        Same rules, but one name lookup for the whole batch instead of 1-3
        queries per taxon (a 1000-row feed page has ~750 distinct taxa).
        Homonym ties still go through find_reference_match so the kingdom
        tie-break stays in one place.

        synonyms: optional {name: accepted ref Taxon} from
        build_synonym_index(); names still unmatched fall back to it with
        match_type 'synonym'. Building the index reads the whole tree, so
        only the batch builder passes it -- never a request.
        '''
        result, plans, names = {}, {}, set()
        for t in taxa:
            if not tree_id:
                result[t.id] = (None, '')
            elif t.tree_id == tree_id:
                result[t.id] = (t, 'direct')
            elif t.rank in ('species', 'subspecies', 'variety', 'form'):
                canonical, binomial, author = parse_scientific_name(t.full_scientific_name)
                if t.canonical_name:
                    canonical = t.canonical_name
                    author = t.author or author
                if not canonical:
                    result[t.id] = (None, '')
                    continue
                plans[t.id] = ('species', t, canonical, binomial, author)
                names.update(x for x in (canonical, binomial) if x)
            else:
                name = (t.canonical_name or t.full_scientific_name or '').strip()
                if name.isupper():  # legacy upper-case family names
                    name = name.capitalize()
                if not name:
                    result[t.id] = (None, '')
                    continue
                plans[t.id] = ('higher', t, name, None, None)
                names.add(name)

        by_name = {}
        if names:
            for c in cls.query.filter(cls.tree_id == tree_id, cls.canonical_name.in_(names)):
                by_name.setdefault(c.canonical_name, []).append(c)

        for tid, (kind, t, name, binomial, author) in plans.items():
            if kind == 'species':
                cands, match_type = by_name.get(name, []), 'canonical'
                if not cands and binomial and name != binomial \
                   and name.split()[-1] == binomial.split()[-1]:
                    cands, match_type = by_name.get(binomial, []), 'autonym'
                if cands and author and (exact := [c for c in cands
                                                   if _norm_author(c.author) == _norm_author(author)]):
                    cands = exact
                    if match_type == 'canonical':
                        match_type = 'exact'
            else:
                cands = [c for c in by_name.get(name, []) if c.rank == t.rank]
                match_type = 'name'

            if not cands:
                ref = synonyms.get(name) if synonyms else None
                if ref is not None and (kind == 'species' or ref.rank == t.rank):
                    result[tid] = (ref, 'synonym')
                else:
                    result[tid] = (None, '')
            elif len(cands) == 1:
                result[tid] = (cands[0], match_type)
            else:
                result[tid] = t.find_reference_match(tree_id, prefer_kingdoms=prefer_kingdoms)
        return result

    @classmethod
    def build_synonym_index(cls, tree_id, kingdoms=None):
        '''{synonym name: accepted Taxon} from the reference tree's
        source_data->>'synonyms' (TaiCOL export: comma-separated canonical
        names, no authors). Names claimed by more than one accepted taxon are
        dropped -- an ambiguous synonym is no match. Misapplied names are not
        used: a specimen filed under a misapplied name is usually the other
        species.

        kingdoms (the site's prefer_kingdoms) limits the index to those
        kingdoms: synonyms cross kingdoms freely (plant genus Thea is also a
        synonym of the ladybird Psyllobora), and a name-only tree such as
        HAST-legacy has no kingdom of its own to tell them apart.'''
        index, ambiguous = {}, set()
        rows = cls.query.filter(cls.tree_id == tree_id,
                                cls.source_data['synonyms'].astext.isnot(None))
        if kingdoms:
            rows = rows.filter(cls.source_data['kingdom'].astext.in_(list(kingdoms)))
        for ref in rows:
            for name in ref.source_data['synonyms'].split(','):
                if not (name := name.strip()) or name in ambiguous:
                    continue
                if name in index and index[name].id != ref.id:
                    ambiguous.add(name)
                    del index[name]
                else:
                    index[name] = ref
        return index

    @classmethod
    def get_reference_matches(cls, taxa, tree_id, prefer_kingdoms=None):
        '''Reference matches for request paths: the stored
        taxon_reference_match rows (built by
        scripts/script-build-taxon-reference-match.py, incl. synonyms and
        curator fixes), and the live name match for taxa with no row yet.
        Read-only. Returns {taxon.id: (ref|None, match_type)}.'''
        if not tree_id:
            return {t.id: (None, '') for t in taxa}
        ids = [t.id for t in taxa if t.tree_id != tree_id]
        result, stored = {}, {}
        if ids:
            rows = session.query(TaxonReferenceMatch, cls).outerjoin(
                cls, cls.id == TaxonReferenceMatch.ref_taxon_id).filter(
                TaxonReferenceMatch.tree_id == tree_id,
                TaxonReferenceMatch.taxon_id.in_(ids))
            stored = {m.taxon_id: (ref, m.match_type if ref else '') for m, ref in rows}
        missing = [t for t in taxa if t.id not in stored]
        result.update(cls.find_reference_matches(missing, tree_id, prefer_kingdoms))
        result.update(stored)
        return result

    def get_higher_taxon(self, rank=''):
        if rank:
            if parents:= self.get_parents():
                for p in parents:
                    if p.rank == rank:
                        return p
        else:
            return self.get_parents()
        return None

    @property
    def parent_id(self):
        rank_index = self.RANK_HIERARCHY.index(self.rank)
        #res = TaxonRelation.query.filter(TaxonRelation.parent_id==self.id).order_by(TaxonRelation.depth).all()
        parent = TaxonRelation.query.filter(TaxonRelation.parent_id==self.id, TaxonRelation.depth==rank_index-1).first()
        #print(self, parent, 'pp',rank_index,flush=True)
        return []

    def to_dict(self, with_meta=False):
        # taxon_family = ''
        # if self.rank != 'family':
        #     if family := self.get_higher_taxon('family'):
        #         taxon_family = family.full_scientific_name
        data = {
            'id': self.id,
            'full_scientific_name': self.full_scientific_name,
            'rank': self.rank,
            'common_name': self.common_name,
            'canonical_name': self.canonical_name,
            'display_name': self.display_name,
            #'display_verbose_name': self.display_verbose_name,
            #'taxon_family': taxon_family,
            #'p': self.parent_id,
        }
        if with_meta is True:
            #set_local
            data['meta'] = {
                'term': 'taxon',
                'label': gettext('物種'),
                'display': data['display_name'],
            }
        return data

    def make_relations(self, rel_data={}):
        if not self.rank or self.rank not in self.RANK_HIERARCHY:
            return None

        rank_index = self.RANK_HIERARCHY.index(self.rank)

        # self relation at depth=0
        if not TaxonRelation.query.filter(
            TaxonRelation.parent_id==self.id,
            TaxonRelation.child_id==self.id,
            TaxonRelation.depth==0,
        ).first():
            session.add(TaxonRelation(parent_id=self.id, child_id=self.id, depth=0))

        # current parents by rank; ranks not submitted are kept as they are
        # (the admin form has no section field, so saving a species must not
        # drop its section)
        parents = {}
        existing = TaxonRelation.query.filter(
            TaxonRelation.child_id==self.id,
            TaxonRelation.depth > 0,
        ).all()
        for rel in existing:
            if rel.parent and rel.parent.rank in self.RANK_HIERARCHY:
                parents[rel.parent.rank] = rel.parent_id

        for rank, pid in rel_data.items():
            if rank not in self.RANK_HIERARCHY:
                continue
            if self.RANK_HIERARCHY.index(rank) >= rank_index:
                continue
            if pid in (None, ''):
                parents.pop(rank, None)
            else:
                parents[rank] = pid

        # rebuild ancestors: depth = path length, nearest parent first
        chain = [r for r in reversed(self.RANK_HIERARCHY[:rank_index]) if r in parents]
        for rel in existing:
            session.delete(rel)
        for depth, rank in enumerate(chain, start=1):
            session.add(TaxonRelation(parent_id=parents[rank], child_id=self.id, depth=depth))

        session.commit()


class TaxonReferenceMatch(Base):
    '''Stored match of a local taxon into a reference tree (e.g. HAST-legacy
    -> TaiCOL). ref_taxon_id NULL = checked, nothing matched. The reference
    taxon carries the external ids (source_id, source_data), so they are not
    copied here. Rows with is_manual are curator decisions: the batch
    builder never overwrites them.'''
    __tablename__ = 'taxon_reference_match'
    __table_args__ = (
        UniqueConstraint('taxon_id', 'tree_id', name='uq_taxon_reference_match_taxon_tree'),
    )
    id = Column(Integer, primary_key=True)
    taxon_id = Column(Integer, ForeignKey('taxon.id', ondelete='CASCADE'), nullable=False)
    tree_id = Column(Integer, ForeignKey('taxon_tree.id', ondelete='CASCADE'), nullable=False)
    ref_taxon_id = Column(Integer, ForeignKey('taxon.id', ondelete='SET NULL'), index=True)
    # exact / canonical / autonym / name / synonym / none / manual
    match_type = Column(String(20), nullable=False)
    is_manual = Column(Boolean, nullable=False, default=False, server_default='false')
    matched_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    note = Column(Text)

    @classmethod
    def upsert(cls, rows):
        '''Insert or refresh computed matches; rows are dicts with taxon_id,
        tree_id, ref_taxon_id, match_type. Curator rows (is_manual) are left
        as they are. Does not commit.'''
        from sqlalchemy.dialects.postgresql import insert
        if not rows:
            return
        stmt = insert(cls).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint='uq_taxon_reference_match_taxon_tree',
            set_={'ref_taxon_id': stmt.excluded.ref_taxon_id,
                  'match_type': stmt.excluded.match_type,
                  'matched_at': func.now()},
            where=cls.is_manual.is_(False))
        session.execute(stmt)
