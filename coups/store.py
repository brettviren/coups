#!/usr/bin/env python3
'''
Interface to database.

All versions are versions, not vunders.
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import os
from sqlalchemy import Table, Column, Integer, String, DateTime
from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.orm import aliased

Base = declarative_base()


ProductManifest = Table(
    "product_manifest", Base.metadata,
    Column('product_id', ForeignKey('product.id'), primary_key=True),
    Column('manifest_id', ForeignKey('manifest.id'), primary_key=True))

ProductQual = Table(
    "product_qual", Base.metadata,
    Column('product_id', ForeignKey('product.id'), primary_key=True),
    Column('qual_id', ForeignKey('qual.id'), primary_key=True))

ManifestQual = Table(
    "manifest_qual", Base.metadata,
    Column('manifest_id', ForeignKey('manifest.id'), primary_key=True),
    Column('qual_id', ForeignKey('qual.id'), primary_key=True))

ProductDependency = Table(
    "product_dependency", Base.metadata,
    Column("id", Integer, primary_key=True),
    # "parent"
    Column("require_id", ForeignKey("product.id")),
    # "child"
    Column("provide_id", ForeignKey("product.id")),
    UniqueConstraint('require_id', 'provide_id', name='uniquedep'),
)


class Flavor(Base):
    __tablename__ = 'flavor'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    products = relationship("Product", backref = "flavor")
    manifests = relationship("Manifest", backref = "flavor")

    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name

class Qual(Base):

    __tablename__ = 'qual'

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False, unique=True)

    products = relationship("Product",
                            secondary=lambda: ProductQual,
                            backref="quals")

    manifests = relationship("Manifest", 
                            secondary=lambda: ManifestQual,
                            backref="quals")
    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name

class Product(Base):
    __tablename__ = 'product'
    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)

    # must NOT be a vunder
    version = Column(String)

    filename = Column(String, unique=True)

    flavor_id = Column(Integer, ForeignKey('flavor.id'), nullable=False)

    manifests = relationship("Manifest",
                             secondary=lambda: ProductManifest,
                             backref="products")

    # A many-to-many for product dependencies.  Terminology:
    # A child depends on a parent.  wirecell (child) depends on boost (parent).
    # As a child we "require" our parents.  dependency.
    # As a parent we "provide" (for) our children. reverse dependency.
    requires = relationship("Product",
                            secondary=lambda: ProductDependency,
                            primaryjoin=id == ProductDependency.c.provide_id,
                            secondaryjoin=id == ProductDependency.c.require_id,
                            backref="provides")

    def __repr__(self):
        quals = self.qualset(":")
        return f'<Product({self.id},{self.name},{self.version},{self.flavor},{quals},{self.filename})>'

    def __str__(self):
        return self.filename

    @property
    def vunder(self):
        return 'v' + self.version.replace(".", "_")

    def qualset(self, delim=None):
        '''
        Return quals as a list or if delim is given as a string
        '''
        qs=[str(q) for q in self.quals]
        qs.sort()
        if delim is None:
            return qs
        return delim.join(qs)


class Manifest(Base):
    __tablename__ = 'manifest'

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)

    # must NOT be a vunder
    version = Column(String)

    filename = Column(String, unique=True)

    flavor_id = Column(Integer, ForeignKey('flavor.id'))

    def __repr__(self):
        quals = ":".join([str(q) for q in self.quals])
        return f'<Manifest({self.id},{self.name},{self.version},{self.flavor},{quals},{self.filename})>'

    def __str__(self):
        return self.filename

    @property
    def vunder(self):
        return 'v' + self.vunder.replace(".", "_")


def engine(url):
    'Get db engine'
    if url is None:
        raise ValueError("no db url given")
    if ":" not in url:          # a file
        url = "sqlite:///"+url
    return create_engine(url, echo=False)    

def init(url):
    'Initialize coups db'
    Base.metadata.create_all(engine(url))

def session(dbname="coups.db", force=False):
    '''
    Return a DB session
    '''
    if not dbname:
        raise ValueError("no db name given");
    if force or not os.path.exists(dbname):
        init(dbname)
    if os.stat(dbname).st_size == 0:
        raise ValueError("db is not initialized")
    Session = sessionmaker(bind=engine(dbname))
    return Session()
