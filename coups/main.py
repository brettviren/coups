#!/usr/bin/env python3
from . import store as cdb
from . import queries, graph

class Coups:
    def __init__(self, store, url):
        self.store_file = store
        self.scisoft_url = url

    @property
    def session(self):
        ses = getattr(self, '_session', None)
        if ses: return ses
        self._session = cdb.session(self.store_file)
        return self._session    


    def qual(self, name):
        '''
        Return a qual object of name, making it if needed.
        '''
        q1 = self.session.query(cdb.Qual).filter_by(name = name).first()
        if q1:
            return q1
        q1 = cdb.Qual(name=name)
        self.session.add(q1)
        return q1

    def flavor(self, name):
        '''
        Return a flavor object of name, making it if needed.
        '''
        f1 = self.session.query(cdb.Flavor).filter_by(name = name).first()
        if f1:
            return f1
        f1 = cdb.Flavor(name=name)
        self.session.add(f1)
        return f1

    def manifest(self, entry, return_existing=False):
        '''
        Return a flavor manifest object, making it if needed.

        If return_existing is true, return a pair (manifest, bool) with
        second value true if the manifest was already existing.
        '''
        from coups.manifest import parse_name

        m1 = self.session.query(cdb.Manifest).filter_by(filename = entry.filename).first()
        if (m1):
            if return_existing:
                return (m1, True)
            return m1

        m1 = cdb.Manifest(name=entry.name, vunder=entry.vunder, filename=entry.filename)
        f1 = self.flavor(entry.flavor)
        m1.flavor = f1
        for q in entry.quals.split(":"):
            q1 = self.qual(q)
            m1.quals.append(q1)
        self.session.add(m1)
        if return_existing:
            return (m1, False)
        return m1

    def product(self, entry, manent=None):
        '''
        Return a product, creating it if needed, attaching it to manifest if given.
        '''
        p1 = self.session.query(cdb.Product).filter_by(filename = entry.filename).first()
        if p1:
            if manent in p1.manifests:
                return p1
            p1.manifests.append(manent)
            return p1
        p1 = cdb.Product(name=entry.name, vunder=entry.vunder, filename=entry.filename)
        if manent:
            p1.manifests.append(manent)
        f1 = self.flavor(entry.flavor)
        p1.flavor = f1
        for q in entry.quals.split(":"):
            q1 = self.qual(q)
            p1.quals.append(q1)
        self.session.add(p1)
        
            
    def names(self, what, field="name"):
        try:
            Table = getattr(cdb, what.capitalize())
        except AttributeError:
            return ()
        ret = list(set([getattr(one, field) for one in self.session.query(Table).all()]))
        ret.sort()
        return ret

    def has_manifest(self, uri):
        '''
        Return true (the db object) if this manifest is in the db, else None
        '''
        from coups.manifest import parse_name
        entry = parse_name(uri)
        return self.session.query(cdb.Manifest).filter_by(filename = entry.filename).first()

    def find_manifests(self, name=None, vunder=None, quals=None, flavor=None, filename=None):
        q = self.session.query(cdb.Manifest)
        if name:
            q = q.filter_by(name = name)
        if vunder:
            # fixme: really we have version, not vunder
            # if vunder[0] != "v":
            #     vunder = "v" + vunder.replace(".","_")
            q = q.filter_by(vunder = vunder)
        if flavor:
            q = q.where(cdb.Manifest.flavor.has(cdb.Flavor.name==str(flavor)))
        if filename:
            q = q.filter_by(filename = filename)
        if not quals:
            return q.all()
        if isinstance(quals, str):
            quals = quals.split(":")
        quals = [str(q) for q in quals] # maybe Qual objects 
        for qual in quals:
            qual = self.session.query(cdb.Qual).filter_by(name=qual).one()
            q = q.where(cdb.Manifest.quals.contains(qual))
        return q.all()
        

    def chain(self, bundle, version, flavor, quals):
        from coups.manifest import b2b

        if bundle not in b2b:
            return []

        if "bundle" in b2b[bundle]:
            print("swap", bundle, b2b[bundle]["bundle"])
            bundle = b2b[bundle]["bundle"]

        mans = self.find_manifests(name=bundle, vunder=version, quals=quals, flavor=flavor)
        if len(mans) != 1:
            print(f'No unique manifest, found: {len(mans)} for {bundle} {version} {flavor} {quals}')
            for m in mans:
                print(m)
            return []
        man = mans[0]

        if bundle not in b2b:
            return mans
        todo = b2b[bundle]
        for subbun in todo.get("has", []):
            print (f'has: {subbun}')
            prod = [p for p in man.products if p.name == subbun]
            if len(prod) != 1:
                print(f'No unique product found for {subbun}: {len(prod)}')
                print(man.products)
                return []
            prod = prod[0]
            version = prod.vunder
            if version.startswith("v"):
                version = version[1:].replace("_",".")
            mans += self.chain(prod.name, version, prod.flavor, prod.quals)
        for subbun in todo.get("ver", []):
            print (f'ver: {subbun}')
            mans += self.chain(subbun, version, flavor, quals)
        return mans


    def load_manifest(self, uri, force=False):
        '''
        Load one new manifest from file or url.
        '''
        from coups.manifest import load, parse_body, parse_name
        man = parse_name(uri)
        man, already = self.manifest(man, True)
        if already and not force:
            return
        text = load(uri)
        for one in parse_body(text):
            self.product(one, man)
        self.session.commit()

    def sub_manifests(self, man, recur = True, seen=None):
        if not man:
            return []
        if isinstance(man, str):
            man = self.has_manifest(man)
        comp = man.pp_compiler
        bld = man.pp_build
        ret = list()
        if seen is None:
            seen = set()
        for prod in man.products:
            if prod.id in seen:
                continue
            seen.add(prod.id)
            q = self.session.query(cdb.Manifest).filter_by(name = prod.name)
            q = q.filter_by(vunder = prod.version)
            q = q.filter_by(flavor = prod.flavor)
            for one in q.all():
                if one.pp_compiler != comp:
                    continue
                if one.pp_build != bld:
                    continue
                ret.append(one)
                if recur:
                    ret += self.sub_manifests(one, True, seen)
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
