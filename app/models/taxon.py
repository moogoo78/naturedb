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
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base
from app.helpers import (
    set_locale,
)

class TaxonTree(Base):

    __tablename__ = 'taxon_tree'
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))
    memo = Column(String(1000))
    # tree_hierarchy

class TaxonRelation(Base):

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

    __tablename__ = 'taxon'
    id = Column(Integer, primary_key=True)
    rank = Column(String(50))
    full_scientific_name = Column(String(500))
    # Botanical
    first_epithet = Column(String(500))
    infraspecific_epithet = Column(String(500)) # final epithet
    author = Column(String(500))
    canonical_name = Column(String(500))
    # status = Column(String(50))

    #dwc.taxonomicStatus: invalid, misapplied, homotypic synonym, accepted
    #dwc.nomenclaturalStatus: nom. ambig., nom. illeg., nom. subnud.

    common_name = Column(String(500)) # abcd: InformalName
    code = Column(String(500))
    tree_id = Column(ForeignKey('taxon_tree.id', ondelete='SET NULL'))
    #provider_source_id =
    provider_id = Column(Integer, ForeignKey('taxon_provider.id', ondelete='SET NULL'))
    provider_source_id = Column(String(500))
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
        s = '[{}] {}'.format(self.rank, self.full_scientific_name)
        if self.common_name:
            s = '{} ({})'.format(s, self.common_name)
        return s

    def get_parents(self):
        res = TaxonRelation.query.filter(TaxonRelation.child_id==self.id, TaxonRelation.parent_id!=self.id).order_by(TaxonRelation.depth).all()
        return [x.parent for x in res]

    def get_children(self, depth=0):
        if depth:
            res = TaxonRelation.query.filter(TaxonRelation.parent_id==self.id, TaxonRelation.depth==depth).all()
        else:
            res = TaxonRelation.query.filter(TaxonRelation.parent_id==self.id).order_by(TaxonRelation.depth).all()
        return [x.child for x in res]

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
        print(self, parent, 'pp',rank_index,flush=True)
        return []

    def to_dict(self, with_meta=False):
        data = {
            'id': self.id,
            'full_scientific_name': self.full_scientific_name,
            'rank': self.rank,
            'common_name': self.common_name,
            'canonical_name': self.canonical_name,
            'display_name': self.display_name,
            #'p': self.parent_id,
        }
        if with_meta is True:
            set_locale()
            data['meta'] = {
                'term': 'taxon',
                'label': '物種',
                'display': data['display_name'],
            }
        return data
