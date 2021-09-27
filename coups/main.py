#!/usr/bin/env python3
'''
A main object used by CLI or embedded into some larger context.

fixme: this has grown organically and needs refactoring.
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import os
import sys
from . import queries, graph
from coups.store import *
from coups import inserts
from sqlalchemy.exc import IntegrityError
import tarfile

class Coups:

    def __init__(self, store, url, force_init=False):
        self.store_file = store
        self.scisoft_url = url
        self.force_init = force_init

    @property
    def session(self):
        ses = getattr(self, '_session', None)
        if ses: return ses
        self._session = session(self.store_file, self.force_init)
        return self._session    


    def query(self, Type, flavor=None, quals=None, **kwds):
        '''
        Return a simple query on Type in (Manifest, Product)
        '''
        return inserts.query(self.session, Type, flavor, quals, **kwds)
        # q = self.session.query(Type).filter_by(**kwds)
        # if flavor:
        #     #print(f"query filter on flavor {flavor}")
        #     q = q.filter(Type.flavor.has(Flavor.name==flavor))
        # if quals:
        #     #print(f"query filter on quals {quals}")
        #     if isinstance(quals, str):
        #         quals = quals.split(":")
        #     for qual in quals:
        #         qt = aliased(Qual)
        #         q = q.join(Type.quals.of_type(qt))
        #         q = q.filter(qt.name == qual)
        # return q

    def qfirst(self, Type, **kwds):
        '''
        Perform query and return first
        '''
        return inserts.qfirst(self.session, Type, **kwds)
        # try:
        #     return self.query(Type, **kwds).first()
        # except IntegrityError:
        #     print(f'{Type} {kwds}')
        #     raise

    def qall(self, Type, **kwds):
        '''
        Perform query and return all
        '''
        return inserts.qall(self.session, Type, **kwds)
        # return self.query(Type, **kwds).all()

    
    def lookup(self, Type, flavor=None, quals=None, **kwds):
        '''
        Return object of Type.

        If kwds resolve a query for object, return first match, else
        create, load and return a new one.
        '''
        return inserts.lookup(self.session, Type, flavor, quals, **kwds)
        # obj = self.qfirst(Type, flavor=flavor, quals=quals, **kwds)
        # if obj:
        #     return obj
        # obj = Type(**kwds)
        # if flavor:
        #     obj.flavor = self.lookup(Flavor, name=flavor)
        # if quals:
        #     if isinstance(quals, str):
        #         quals = quals.split(":")
        #     for qual in quals:
        #         obj.quals.append(self.lookup(Qual, name=qual))
        # self.session.add(obj)
        # return obj


    def qual(self, name):
        '''
        Return a qual object of name, making it if needed.
        '''
        return inserts.qual(self.session, name)
        # if name is None:
        #     raise ValueError("qualifier of None is illegal")
        # if not name:
        #     raise ValueError("empty qualifier is illegal")

        # q1 = self.session.query(Qual).filter_by(name = name).all()
        # if q1:
        #     return q1[0]
        # q1 = Qual(name=name)
        # self.session.add(q1)
        # return q1

    def flavor(self, name):
        '''
        Return a flavor object of name, making it if needed.
        '''
        return inserts.flavor(self.session, name)
        # f1 = self.session.query(Flavor).filter_by(name = name).first()
        # if f1:
        #     return f1
        # f1 = Flavor(name=name)
        # self.session.add(f1)
        # return f1

    def manifest(self, mtp, return_existing=False):
        '''
        Return a manifest object, making it if needed.

        The mtp is a manifest.Manifest tuple object.

        If return_existing is true, return a pair (manifest, bool) with
        second value true if the manifest was already existing.
        '''
        return inserts.manifest(self.session, mtp, return_existing)
        # m1 = queries.manifest(self.session, mtp)
        # if m1:
        #     if return_existing:
        #         return (m1, True)
        #     return m1

        # quals = list()
        # if mtp.quals:
        #     for q in mtp.quals.split(":"):
        #         quals.append(self.qual(q))

        # flavor = self.flavor(mtp.flavor)
        # m1 = Manifest(name=mtp.name, version=mtp.version,
        #               flavor=flavor, quals=quals,
        #               filename=mtp.filename)
        # self.session.add(m1)
        # if return_existing:
        #     return (m1, False)
        # return m1

    def product(self, ptp, return_existing=False):
        '''
        Return a product, given a manifest.Product tuple.

        If it is not yet in the DB, it will be added.
        '''
        return inserts.product(self.session, ptp, return_existing)
        # pobj = self.session.query(Product).filter_by(filename = ptp.filename).first()
        # if pobj:
        #     if return_existing:
        #         return pobj, True
        #     return pobj

        # pobj = Product(name=ptp.name, version=ptp.version, filename=ptp.filename)
        # pobj.flavor = self.flavor(ptp.flavor)
        # if ptp.quals:
        #     for q in ptp.quals.split(":"):
        #         q1 = self.qual(q)
        #         pobj.quals.append(q1)
        # self.session.add(pobj)
        # if return_existing:
        #     return pobj, False
        # return pobj
            
    def names(self, what, field="name"):
        '''
        Return list of names of manifests or products
        ''' 
        import coups.store
        try:
            Table = getattr(coups.store, what.capitalize())
        except AttributeError:
            return ()
        ret = list(set([getattr(one, field) for one in self.session.query(Table).all()]))
        ret.sort()
        return ret

    def has_manifest(self, mf):
        '''
        Return true (the db object) if this manifest is in the db, else None.

        The manifest should be a manifest.Manifest tuple.
        '''
        if not isinstance(mf, str):
            mf = mf.filename
        return self.session.query(Manifest).filter_by(filename = mf).first()

    def remove_manifest(self, man):
        '''
        Remove the manifest object from the DB.
        '''
        self.session.delete(man)
        self.session.commit()

    def load_dependencies(self, child, parents, commit=True):
        '''
        Load product dependencies to DB from objects.

        A child depends on its parents.  
        Eg, wirecell (child) depends on boost (parent).
        '''
        child.requires = set(child.requires + parents)
        if commit:
            self.session.commit()

    def load_deps_text(self, text, commit=True):
        '''
        Parse text from 'ups depend' and load dependencies for first
        product.  Return list of seed followed by parent products.
        '''
        from coups import depend
        from coups.queries import products
        entries = depend.parse(text)
        top = entries[0]
        child = products(self.session, top.name, top.version, top.flavor, top.quals)
        if not child:
            raise ValueError(f"No unique child product: {top[:-1]}, got {len(child)}")
        child = child[0]

        ret = [child]
        for ent in entries[1:]:
            if ent.name in top.parents:
                parent = products(self.session, ent.name, ent.version, ent.flavor, ent.quals)
                if not parent:
                    sys.stderr.write(f"No unique parent product: {ent[:-1]}, got {len(parent)}")
                    continue
                parent = parent[0]
                ret.append(parent)
                if parent in child.provides:
                    continue
                child.provides.append(parent)
        if commit:
            self.session.commit()
        return ret


    def commit(self, *objs):
        for obj in objs:
            self.session.add(obj)
        self.session.commit()


    def edges_from_m(self, m, distance=1):
        edges = set()
        if not distance:
            return edges
        for p in m.products:
            edges.add((m,p))
            edges.update(self.edges_from_p(p, distance-1))
        return edges
    def edges_from_p(self, p, distance=1):
        edges = set()
        if not distance:
            return edges
        for m in p.manifests:
            edges.add((m,p))
            edges.update(self.edges_from_m(m, distance-1))
        return edges

    def graph_product(self, name, version=None, flavor=None, quals=None, distance=2):
        '''
        Return a graph centered around a product.

        The distance determines how far to extend the graph.  
        Distance of 1 will include manifests feature the product.
        Distance of 2 will include products of those manifests.
        Distance of 3 will include manifests of those produts, etc.
        '''
        edges = set()

        ps = queries.products(self.session, name, version, flavor, quals)
        if not ps:
            raise ValueError(f'No products name={name} version:{version} flavor:{flavor} quals:{quals}')
        for p in ps:
            edges.update(self.edges_from_p(p, distance))

        return graph.from_edges(edges)

    def graph_manifest(self, name, version=None, flavor=None, quals=None, distance=2):
        '''
        Like graph_product but center on a manifest
        '''
        edges = set()

        ms = queries.manifests(self.session, name, version, flavor, quals)
        if not ms:
            raise ValueError(f'No manifests name={name} version:{version} flavor:{flavor} quals:{quals}')
        for m in ms:
            edges.update(self.edges_from_m(m, distance))

        return graph.from_edges(edges)

    def product_dependencies(self, tdat):
        '''
        Return a tuple (seed, deps) from a parsed table data.

        Each element in the list represents the information one flavor
        block of the table.

        "seed" is a product tuple object representing the flavored
        product itself

        "deps" is a list of "dependency" objects that give a product
        tuple of a dependency and indication if it is required or
        optional.

        Note, the tdat should be in "old" or "simple" form.  
        See coups.table.simplify()
        '''
        from coups.product import make as make_product
        from coups.util import versionify
        name = tdat['product']
        version = versionify(tdat['vunder'])
        fdat = tdat['flavorblock']
        flavor = fdat['flavor']
        quals = fdat['qualifiers']
        seed = make_product(name, version, flavor, quals)
        deps = list()
        for act in tdat['flavorblock']['actions']:
            if act['action'].lower() != 'setup':
                continue
            for cmd in act['commands']:
                if cmd['command'].lower() not in ("setuprequired","setupoptional"):
                    continue
                al = cmd['arglist']
                parts = al[0].split() # fixme: this should added to parser
                n = parts.pop(0)
                v=q=""
                if parts:
                    v = parts.pop(0)
                else:
                    # fscking indirection to current.chain
                    sys.stderr.write(f'no version, ignoring dependency for {n}! (need chain indirection support)')
                    continue
                if parts:
                    rest = ''.join(parts)
                    assert rest.startswith("-q")
                    q = rest[2:].replace("+","").strip()
                # fixme: is it really true that flavor is common and never specified with a -f?
                dep = make_product(n, v, flavor, q)
                deps.append(dep)
        return (seed, deps)

    def pack_manifest(self, seed, paths=(), outdir='.'):
        '''
        Produce product tar file for seed and any it depends on.

        This prefers to download product tar files from Scisoft but if
        a required product is served there an attempt will be made to
        repack from UPS installation areas found at "paths".
        '''
        
