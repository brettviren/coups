#!/usr/bin/env python3
'''
Ensconce various write (insert) queries 
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups import queries
from coups.store import *

def query(ses, Type, flavor=None, quals=None, **kwds):
    '''
    Return a simple query on Type in (Manifest, Product)
    '''
    q = ses.query(Type).filter_by(**kwds)
    if flavor:
        #print(f"query filter on flavor {flavor}")
        q = q.filter(Type.flavor.has(Flavor.name==flavor))
    if quals:
        #print(f"query filter on quals {quals}")
        if isinstance(quals, str):
            quals = quals.split(":")
        for qual in quals:
            qt = aliased(Qual)
            q = q.join(Type.quals.of_type(qt))
            q = q.filter(qt.name == qual)
    return q

def qfirst(ses, Type, **kwds):
    '''
    Perform query and return first
    '''
    try:
        return query(ses, Type, **kwds).first()
    except IntegrityError:
        print(f'{Type} {kwds}')
        raise

def qall(ses, Type, **kwds):
    '''
    Perform query and return all
    '''
    return query(ses, Type, **kwds).all()


def lookup(ses, Type, flavor=None, quals=None, **kwds):
    '''
    Return object of Type.

    If kwds resolve a query for object, return first match, else
    create, load and return a new one.
    '''
    obj = qfirst(ses, Type, flavor=flavor, quals=quals, **kwds)
    if obj:
        return obj
    obj = Type(**kwds)
    if flavor:
        obj.flavor = lookup(ses, Flavor, name=flavor)
    if quals:
        if isinstance(quals, str):
            quals = quals.split(":")
        for qual in quals:
            obj.quals.append(lookup(ses, Qual, name=qual))
    ses.add(obj)
    return obj


def qual(ses, name):
    '''
    Return a qual object of name, making it if needed.
    '''
    if name is None:
        raise ValueError("qualifier of None is illegal")
    if not name:
        raise ValueError("empty qualifier is illegal")

    q1 = ses.query(Qual).filter_by(name = name).all()
    if q1:
        return q1[0]
    q1 = Qual(name=name)
    ses.add(q1)
    return q1

def flavor(ses, name):
    '''
    Return a flavor object of name, making it if needed.
    '''
    f1 = ses.query(Flavor).filter_by(name = name).first()
    if f1:
        return f1
    f1 = Flavor(name=name)
    ses.add(f1)
    return f1

def manifest(ses, mtp, return_existing=False):
    '''
    Return a manifest object, making it if needed.

    The mtp is a manifest.Manifest tuple object.

    If return_existing is true, return a pair (manifest, bool) with
    second value true if the manifest was already existing.
    '''
    m1 = queries.manifest(ses, mtp)
    if m1:
        if return_existing:
            return (m1, True)
        return m1

    quals = list()
    if mtp.quals:
        for q in mtp.quals.split(":"):
            quals.append(qual(ses, q))

    flav = flavor(ses, mtp.flavor)
    m1 = Manifest(name=mtp.name, version=mtp.version,
                  flavor=flav, quals=quals,
                  filename=mtp.filename)
    ses.add(m1)
    if return_existing:
        return (m1, False)
    return m1

def product(ses, ptp, return_existing=False):
    '''
    Return a product, given a manifest.Product tuple.

    If it is not yet in the DB, it will be added.
    '''
    pobj = ses.query(Product).filter_by(filename = ptp.filename).first()
    if pobj:
        if return_existing:
            return pobj, True
        return pobj

    pobj = Product(name=ptp.name, version=ptp.version, filename=ptp.filename)
    pobj.flavor = flavor(ses, ptp.flavor)
    if ptp.quals:
        for q in ptp.quals.split(":"):
            q1 = qual(ses, q)
            pobj.quals.append(q1)
    ses.add(pobj)
    if return_existing:
        return pobj, False
    return pobj
