#!/usr/bin/env python3
'''
Handle manipacks (manifest + packed product tar files)
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import functools
from pathlib import Path
import json
import networkx
from networkx.algorithms.dag import topological_sort

import coups.manifest
import coups.scisoft
import coups.inserts
import coups.render
import coups.ups

class Manipack:

    def __init__(self, manifest, session=None, upsdbs=None):
        '''
        Create a manipack = manifest + packed product tar files

        The parent directory of the <manifest> pathlib.Path will be
        filled with tar files.

        Provide list of UPS "$PRODUCTS" directories as <upsdbs> if
        repacking will be required.

        The <session> is optional but must be given if coups DB will
        provides missing information and to record products and
        manifest.
        '''
        if isinstance(manifest, str):
            manifest = Path(manifest)
        self.mtp = coups.manifest.parse_filename(manifest.name)
        self.outdir = manifest.parent
        if not self.outdir.exists():
            self.outdir.mkdir(parents=True)
        self.manifest = manifest
        self.upsdbs = upsdbs
        self.session = session
        self.seeds = list()
        self.deps = networkx.DiGraph()

    def __str__(self):
        return f'{self.manifest}'

    def manifest_seed(self, manifest):
        '''
        Read named <manifest> file and add each product as a seed.

        The <manifest> is sourced in order as: local file, coups DB,
        Scisoft URL.

        Result is added to coups DB
        '''
        if manifest is None:
            return

        p = Path(manifest)
        seeds = list()
        if p.exits():
            seeds = coups.manifest.parse_body(p.open().read())
        if not seeds:
            seeds = coups.scisoft.manifest_products(manifest)
        if not text:
            mtp = coups.manifest.parse_filename(manifest)
            mobj = coups.queries.manifest(mtp)
            seeds = [coups.product.make(p.name, p.version, p.flavor, p.quals, p.filename) for p in mobj.products]
        if not seeds:
            raise ValueError(f'can not read manifest {manifest}')
        for seed in seeds:
            self.add_seed(seed)

    def add_seed(self, seed):
        '''
        Add a seeding product
        '''
        if not all((seed.name, seed.version, seed.flavor)):
            raise ValueError(f'illdefined seed: {seed}')
        self.seeds.append(seed)
            
    def product_seed(self, name, version, flavor, quals):
        'Add a single product as a seed'
        prod = self._resolve_four(name, version, flavor, quals)
        self.add_seed(prod)

    def _record(self):
        '''
        If we have a session, record manifest and products to coups DB.
        '''
        if not self.session:
            return
        mobj, had = coups.inserts.manifest(self.session, self.mtp, True)
        if had:
            mobj.products.clear()
        for node in self.deps:
            prod = self.deps.nodes[node]["obj"]
            pobj = coups.inserts.product(self.session, prod)
            mobj.products.append(pobj)
        self.session.commit()

    def render(self, renderer=coups.render.product_manifest):
        '''
        Return text of our manifest as toplological sorted list of
        dependency graph nodes.
        '''
        nodes = list(topological_sort(self.deps))
        nodes.reverse()
        lines = list()
        for node in nodes:
            prod = self.deps.nodes[node]["obj"]
            line = renderer(prod)
            lines.append(line)
        lines.append("")        # end file with newline
        return '\n'.join(lines)

    def _assure_tarfile(self, prod):
        '''
        Assure tarfile for prod is in outdir.  If not, try to get from
        scisoft.  If fail, try to repace from UPS.
        '''
        path = self.outdir / prod.filename
        if path.exists():
            return path
        try:
            return coups.scisoft.download_product(prod, self.outdir)
        except coups.scisoft.HTTPError:
            pass
        return coups.ups.tarball(prod, self.upsdbs, self.outdir)
        
    @functools.cache
    def _resolve_tdat(self, sdat, prod):
        '''
        Return tdat (parsed and narrowed table data structure)
        corresponding to sdat (parsed argstr data structure) in
        context of parent product.

        As a side effect this will produce a new tar file if sdat
        matches no seeds nor existing products in the graph.

        sdat can be incomplete w.r.t. version and a chain will be used
        to try to resolve it.
        '''
        print(f'sdat: {sdat}')
        name = sdat['product']
        version = None
        if 'vunder' in sdat:
            version = versionify(sdat['vunder'])
        flavor = sdat.get('flavor', prod.flavor)
        quals = ":".join(sdat.get('quals', prod.quals.split(":")))
        want = self._resolve_four(self, name, version, flavor, quals)
        got = coups.ups.tarball(want, self.upsdbs, self.outdir)
        return self._get_tdat(want)

    def _resolve_four(self, name, version, flavor, quals):
        '''
        Return matching product.
        '''
        four = (name, version, flavor, quals)
        print(f'resolving: {four}')
        tries = set(self.seeds + [self.deps.nodes[n]['obj'] for n in self.deps.nodes])
        for one in tries:
            if one[:4] == four:
                ret = self._get_tdat(one)
                print(f'resolved: {ret}')
                return ret

        if not version:
            version, quals = coups.ups.chain_version_quals(name, flavor, self.upsdbs, approx=True)
        
        want = coups.product.make(name, version, flavor, quals)
        print(f'resolved: {want}')
        return want

    @functools.cache
    def _get_tdat(self, prod):
        '''
        Return a "tdat" derived from a UPS table file in a product tar
        file corresponding to prod.

        Assures the tar file is in the outdir as a side-effect. 
        '''
        tfile = self.outdir / prod.filename
        if not tfile.exists():
            tfile = self._assure_tarfile(prod)
        text = coups.ups.table_in_tar(tfile)
        tdat = coups.table.parse(text, prod)
        return tdat

    @functools.cache
    def _get_deps(self, prod):
        '''
        Return list of products which on which prdocut prod depends.
        '''
        tdat = self._get_tdat(prod)
        return coups.table.deps(tdat, self._resolve_tdat, prod)

    def _add_node(self, prod):
        '''
        Add product as a node
        '''
        node = self._id(prod)
        if node in self.deps:
            return
        return self.deps.add_node(node, obj=prod)

    def _add_edge(self, tail, head, **attr):
        '''
        Add an edge FROM <tail> TO <head>, both product tuple objects
        '''
        return self.deps.add_edge(self._id(tail), self._id(head), **attr)

    def _id(self, prod):
        '''
        Return an identifier for a product tuple object
        '''
        return prod.filename

    def _process_one(self, prod):
        '''
        Process one product provided as a product.Product tuple object.
        '''
        if self._id(prod) in self.deps:
            return
        self._add_node(prod)
        deps = self._get_deps(prod)
        print(f'manipack: deps: {deps}')
        for pair in deps:
            for dep in pair:    # could differentiate req/opt
                if not dep: continue
                self._process_one(dep)
                self.add_edge(prod, dep)

    def commit(self):
        '''
        Process seeds, write manifest file and produce tar files.

        If session given, record manifest and products to coups DB.
        '''
        for seed in self.seeds:
            print(f'processing {seed}')
            self._process_one(seed)
        self.manifest.open("w").write(self.render())
        self._record()
