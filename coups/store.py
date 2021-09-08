#!/usr/bin/env python3
'''
Interface to database.
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

build_types = ("prof", "debug")
def separate_quals(quals):
    '''
    Given a list of quals, return a tuple.

    First element is the list of quals with the build type removed and
    second is the build type string.
    '''
    qs = list()
    bt = None
    for q in quals:
        q = str(q)
        if q in build_types:
            bt = q
        else:
            qs.append(q)
    return (qs, bt)

def build_qual(quals):
    '''
    Find and return the build qualifier.
    '''
    quals = [str(q) for q in quals]
    for q in quals:
        if q in build_types:
            return q
    raise ValueError(f'No build qual found in {quals}')

def nonbuild_qual(quals):
    '''
    Return non build quals
    '''
    bq = build_qual(quals)
    cq = compiler_qual(quals)
    nix = [bq,cq]
    ret = list()
    quals = [str(q) for q in quals]
    for qual in quals:
        if qual in nix:
            continue
        ret.append(qual)
    ret.append(cq)
    return ret

# fixme: these shoudl be in the database, no?
# From a recent pullProducts + some sleuthing.
# see also https://cdcvs.fnal.gov/redmine/projects/cet-is-public/wiki/AboutQualifiers
platform_flavors = {
    "Linux64bit+2.6-2.5": "slf5",
    "Linux64bit+2.6-2.12": "slf6",
    "Linux64bit+3.10-2.17": "slf7",
    # note, pullProducts reverses the definitions of "arch" and
    # "platform".  What we call "platform" it calls "myarch".  In any
    # case, flavor flattens platform + architecture.
    "Linuxppc64le64bit+3.10-2.17": "slf7",
    "Linux64bit+3.19-2.19": "u14",
    "Linux64bit+4.4-2.23": "u16",
    "Linux64bit+4.15-2.27": "u18",
    "Linux64bit+5.4-2.31": "u20",
    # Another example of plat/arch degeneracy.
    "Darwin+12": "d12",
    "Darwin64bit+12": "d12",
    "Darwin64bit+13": "d13",
    "Darwin64bit+14": "d14",
    "Darwin64bit+15": "d15",
    "Darwin64bit+16": "d16",
    "Darwin64bit+17": "d17",
    "Darwin64bit+18": "d18",
    "source": "source",
}
    

def platform_flavor(flavor):
    '''
    Return the platform code guessed from the flavor
    slf5, slf6, slf7, d14, d15, d16, d17, d18, u14, u16, u18, u20
    '''
    flavor = str(flavor)
    try:
        return platform_flavors[flavor]
    except:
        pass
    # Make this family of functions all throw same
    raise ValueError(f'No platform for flavor: {flavor}')

compiler_qual_prefix = ("c", "e")
def compiler_qual(quals):
    '''
    Find and return the compiler qualifier.
    '''
    quals = [str(q) for q in quals]
    for q in quals:
        for pre in compiler_qual_prefix:
            if q.startswith(pre):
                rest = q[len(pre):]
                try:
                    num = int(rest)
                except ValueError:
                    continue
                return q
    raise ValueError(f'No compiler qual found in {quals}')

class Product(Base):
    __tablename__ = 'product'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    vunder = Column(String)
    filename = Column(String, unique=True)

    flavor_id = Column(Integer, ForeignKey('flavor.id'))

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
        quals = ":".join([str(q) for q in self.quals])
        return f'<Product({self.id},{self.name},{self.vunder},{self.flavor},{quals},{self.filename})>'

    def __str__(self):
        qs,bt = separate_quals(self.quals)
        quals = ":".join(qs)
        if bt:
            quals += f':{bt}'
        if quals:
            quals = f'-q {quals}'
        flav = str(self.flavor)
        if flav:
            flav = f'-f {flav}'
        return f'{self.name} {self.vunder} {self.filename} {flav} {quals}'

    @property
    def tuple(self):
        quals = [str(q) for q in self.quals]
        quals.sort()
        return (self.name, self.version, self.flavor, quals)

    @property
    def version(self):
        v = self.vunder.replace('_','.')
        if v[0] == 'v':
            v = v[1:]
        return v
    @property
    def dashquals(self):
        return self.quals.replace(":","-")

    @property
    def pp_platform(self):
        'Return like slf7, d12'
        return platform_flavor(self.flavor)

    @property
    def pp_namever(self):
        'Return like <name>-v<under> for pull products line'
        return f'{self.name}-{self.vunderfy}'
    @property
    def pp_compiler(self):
        'Return compiler qual'
        return compiler_qual(self.quals)
    @property
    def pp_build(self):
        'Return build qual'
        return build_qual(self.quals)

    @property
    def manifest_line(self):
        # 0{name} 21{vunder} 37{tarball} 98{-f flavor} 125{-a q1:q2}
        ret = f'{self.name:21}{self.vunder:16}{self.filename:61}'
        flav = 'NULL'
        if self.flavor:
            flav = str(self.flavor)
        ret += f'-f {flav:24}'
        q = ":".join([str(q) for q in self.quals])
        if q:
            ret += f'-q {q}'
        return ret

class Manifest(Base):
    __tablename__ = 'manifest'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # Fixme: change this name to "version" as it is like 3.06.03 not in vunderform.
    # When done, change vunderfy() to vunder() below.
    vunder = Column(String)
    filename = Column(String, unique=True)

    flavor_id = Column(Integer, ForeignKey('flavor.id'))

    def __repr__(self):
        quals = ":".join([str(q) for q in self.quals])
        return f'<Manifest({self.id},{self.name},{self.vunder},{self.flavor},{quals},{self.filename})>'

    def __str__(self):
        return self.filename

    @property
    def vunderfy(self):
        return 'v' + self.vunder.replace(".", "_")

    @property
    def pp_platform(self):
        'Return like slf7, d12'
        return platform_flavor(self.flavor)

    @property
    def pp_namever(self):
        'Return like <name>-v<under> for pull products line'
        return f'{self.name}-{self.vunderfy}'

    @property
    def pp_compiler(self):
        'Return compiler qual'
        return compiler_qual(self.quals)

    @property
    def pp_build(self):
        'Return build qual'
        return build_qual(self.quals)
    
    @property
    def pp_nonbuild(self):
        return nonbuild_qual(self.quals)


    @property
    def tuple(self):
        quals = [str(q) for q in self.quals]
        quals.sort()
        return (self.name, self.version, self.flavor, quals)


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
