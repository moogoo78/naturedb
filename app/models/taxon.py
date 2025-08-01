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
    desc,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import (
    Base,
    session
)

class TaxonTree(Base):

    __tablename__ = 'taxon_tree'
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))
    memo = Column(String(1000))
    # tree_hierarchy

class TaxonRelation(Base):
    '''closure table
    '''
    __tablename__ = 'taxon_relation'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('taxon.id', ondelete='SET NULL'))
    child_id = Column(Integer, ForeignKey('taxon.id', ondelete='SET NULL'))
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
    RANK_HIERARCHY = ['family', 'genus', 'species']

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
    #provider_source_id =
    #provider_id = Column(Integer, ForeignKey('taxon_provider.id', ondelete='SET NULL'))
    #provider_source_id = Column(String(500))
    is_accepted = Column(Boolean, default=False)
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
        return [x.child for x in res]

    def get_siblings(self):
        if self.rank_depth == 0:
            taxa = Taxon.query.filter(Taxon.rank==Taxon.RANK_HIERARCHY[0]).order_by(Taxon.full_scientific_name).all()
            return taxa
        else:
            if tr := TaxonRelation.query.filter(TaxonRelation.child_id==self.id, TaxonRelation.depth==1).first():
                return tr.parent.get_children(1)
        return []

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
        if not self.rank:
            return None

        rank_index = self.RANK_HIERARCHY.index(self.rank)

        # self relation
        if x := TaxonRelation.query.filter(TaxonRelation.parent_id==self.id, TaxonRelation.child_id==self.id, TaxonRelation.depth==0).first():
            pass
        else:
            taxon_rel_0 = TaxonRelation(parent_id=self.id, child_id=self.id, depth=0)
            session.add(taxon_rel_0)

        # higher relations
        for rank, pid in rel_data.items():
            parent_index = self.RANK_HIERARCHY.index(rank)
            if x := TaxonRelation.query.filter(TaxonRelation.child_id==self.id, TaxonRelation.depth==rank_index-parent_index).first():
                x.parent_id = pid
            else:
                taxon_rel_x = TaxonRelation(parent_id=pid, child_id=self.id, depth=rank_index-parent_index)
                session.add(taxon_rel_x)
        session.commit()
