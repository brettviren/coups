#!/usr/bin/env python3
'''
Ensconce various queries 
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from sqlalchemy.orm import aliased
from coups.manifest import cmp as manifest_cmp
from coups.store import *
from coups.util import vunderify, versionify

def subsets(ses, man, diff=0):
    '''
    Return a list of manifests that provide a subset of man.

    Another manifest, "other" is considered a subset if the
    cardinality of the set difference of "man" - "other" is "diff" or
    less.

    Note, the query is based on sets of products.
    '''
    diff *= -1

    mids = ses.execute(f'SELECT subset.manifest_id FROM product_manifest AS subset GROUP BY subset.manifest_id HAVING SUM(subset.product_id IN (select product_id FROM product_manifest WHERE manifest_id = {man.id})) - count(*) >= {diff}')
    mids = [m[0] for m in mids.all()]
    return ses.query(Manifest).filter(Manifest.id.in_(mids)).all()


# sqlite> select * from manifest where id IN (
#     SELECT subset.manifest_id FROM product_manifest as subset GROUP BY subset.manifest_id HAVING SUM(subset.product_id IN (SELECT product_id FROM product_manifest WHERE manifest_id =15786)) - count(*) <= -1);



def find_bundles(man, other_mans):
    '''
    Given a manifest object man, return other manifest objects which
    provide.
    '''
    # fixme: this is exhaustive and dumb.  We could still be
    # exhaustive if we did the set calculus in the db....
    ret = list()
    # other_mans = ses.query(store.Manifest).all()
    for other in other_mans:
        if man.name == other.name:
            continue
        mine, both, yours = manifest_cmp(man, other)
        if mine > 0 and both > 0 and yours == 0:
            ret.append(other)
        #print (f'no match: ({mine},{both},{yours}) {other}')
    return ret

def qualified(ses, Type, name, version=None, flavor=None, quals=None):
    '''
    Return matching records of Type (manifest or products).
    '''
    p = ses.query(Type)
    p = p.filter(Type.name==name)
    if version:
        p = p.filter(Type.version==version)
    if flavor:
        p = p.filter(Type.flavor.has(Flavor.name==flavor))
    if quals:
        if isinstance(quals, str):
            quals = quals.split(":")
        for qual in quals:
            qt = aliased(Qual)
            p = p.join(Type.quals.of_type(qt))
            p = p.filter(qt.name == qual)
    return p.all()

def products(ses, name, version=None, flavor=None, quals=None):
    '''
    Return matching products.
    '''
    return qualified(ses, Product, name, version, flavor, quals)

def manifest(ses, mtp):
    '''
    Return manifest matching the given Manifest tuple or None
    '''
    got = qualified(ses, Manifest, mtp.name, mtp.version, mtp.flavor, mtp.quals)
    if got:
        return got[0]
    return None

def manifests(ses, name, version=None, flavor=None, quals=None):
    '''
    Return matching manifests.
    '''
    version = versionify(version)
    return qualified(ses, Manifest, name, version, flavor, quals)


