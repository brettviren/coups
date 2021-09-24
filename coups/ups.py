#!/usr/bin/env python3
'''
Handle installed UPS product area. 

We *always* encode a "version" not a "vunder" but we may render to a
"vunder".
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import sys
import json                     # for dump/debug
import functools
from coups.product import make as make_product
from coups.util import vunderify, versionify
import coups.table

from coups.quals import dashed as dashed_quals
import networkx as nx

from pathlib import Path
import tarfile


import os

def env(varname, delim=None, default=""):
    got = os.environ.get(varname, default)
    if got is None:
        return
    if delim:
        return got.split(delim)
    return got


def resolve(name, paths=None):
    '''
    Return list of pathlib.Path object by locating "name" in paths.
    '''
    if not paths:
        paths = list()

    paths += env("PRODUCTS", ":")

    ret = list()
    for path in map(Path, paths):
        maybe = path / name
        if maybe.exists():
            ret.append(maybe)
    return ret


def setting(settings, key):
    '''
    Return all values in settings block matching the key

    Key is case insensitive but values are returned as-is.
    '''
    return [x['val'] for x in settings if x['key'].lower() == key.lower()]


class ChainFile:
    '''
    Represent a UPS chain file
    '''

    def __init__(self, name,  chain="current", dbs=None):
        '''
        Find chain file for named product.

        A chain "file" associates (name,flavor)->(version,qualifers)

        The '.chain' "file" may actually be a directory of chain files.
        When encountered they are combined.

        Return a parsed ChainFile as a dictionary.
        '''
        relfname = f'{name}/{chain}.chain'
        paths = resolve(relfname, dbs)
        if not paths:
            raise ValueError(f'no file for chain {chain} for {name}')
        path = paths[0]
        if path.is_dir():
            files = path.glob("*")
        else:
            files = [path]

        ret = None
        for one in files:
            cdat = coups.table.ChainFile.parse_string(one.open().read()).as_dict()
            if not ret:
                ret = cdat
                continue
            ret['chainblocks'] += cdat['chainblocks']
        self.dat = ret


    @property
    def name(self):
        return self.dat["product"]

    @property
    def chain(self):
        return self.dat["chain"]

    def version_quals(self, flavor):
        'Return tuple (version,quals) for flavor'
        for cb in self.dat["chainblocks"]:
            if cb["flavor"] == flavor:
                return versionify(cb["vunder"]), cb["qualifiers"]
        raise ValueError(f'no flavor {flavor} in chain {self.chain} for product {self.name}')


class VersionFile:
    '''
    Represent a UPS version file

    A version "file" associates (name,version,flavor)->(table) 

    '''

    def __init__(self, name, version, dbs=None):
        '''
        Find version file for named product.

        The '.chain' "file" may actually be a directory of chain files.
        When encountered they are combined.

        Return a parsed ChainFile as a dictionary.
        '''

        vunder = vunderify(version)

        paths = resolve(f'{name}/{vunder}.version', dbs)
        if not paths:
            raise ValueError(f'no version file for {name} version {version}')
        # print(paths)

        path = paths[0]
        if path.is_dir():
           files = path.glob("*")
        else:
            files = [path]

        ret = None
        for one in files:
            vdat = coups.table.VersionFile.parse_string(one.open().read()).as_dict()
            if not ret:
                ret = vdat
                continue
            ret['versionblocks'] += vdat['versionblocks']
        self.dat = ret



class Command:
    def __init__(self, dat):
        self.dat = dat
        
    @property
    def name(self):
        return self.dat['command']

    @property
    def argstr(self):
        return self.dat['argstr']


class Action:
    def __init__(self, dat):
        self.dat = dat

    @property
    def name(self):
        return self.dat['action'].lower()

    @property
    def commands(self):
        for one in self.dat['commands']:
            yield Command(one)


    
class TableFile:
    def __init__(self, tdat, dbs):
        self.dat = tdat
        self.dbs = dbs          # broader context
        
    @property
    def name(self):
        return self.dat["product"]
    @property
    def vunder(self):
        return self.dat["vunder"]
    @property
    def version(self):
        return versionify(self.vunder)
    @property
    def flavor(self):
        return self.dat["flavorblock"]["flavor"]
    @property
    def quals(self):
        return self.dat["flavorblock"]["qualifiers"]

    @property
    def tuple(self):
        return make_product(self.name, self.version, self.flavor, self.quals)

    def __str__(self):
        return ' '.join([self.name, self.version, self.flavor, self.quals])
        
    def __repr__(self):
        string = str(self)
        return f'<TableFile {string}>'

    @property
    def actions(self):
        fb = self.dat['flavorblock']        
        ablks = fb.get("actions", [])
        for one in ablks:
            yield Action(one)

    @functools.lru_cache
    def required_table(self, argstr):
        '''
        Parse a setupRequired() or setupOptional() argstr and return a
        corresponding product TableFile.
        '''
        adat = coups.table.SetupString.parse_string(argstr)
        version = adat.get('vunder', None)
        flavor = adat.get('flavor', self.flavor)
        quals = ':'.join(adat.get('quals', []))
        return product_table(adat['product'], version, flavor, quals, self.dbs)

    @functools.cached_property
    def deps(self):
        req = list()
        opt = list()
        for act in self.actions:
            print(f'{self.name} action: {act.name}')
            if act.name != 'setup':
                continue
            for cmd in act.commands:
                if cmd.name.lower() == 'setuprequired':
                    req.append(self.required_table(cmd.argstr))
                if cmd.name.lower() == 'setupoptional':
                    opt.append(self.required_table(cmd.argstr))
        return (req, opt)
                    

class TableFileMultiFlavor:
    '''
    Represent a UPS version file
    '''
    def __init__(self, name, version, tdat=None, dbs=None):
        '''
        Find a table file
        '''
        self.name = name
        self.version = versionify(version)
        self.dbs = dbs

        vunder = vunderify(version)

        # some hard wired locations.
        tries = [
            f'{name}/{name}.table',
            f'{name}/{vunder}.table',
            f'{name}/{vunder}/ups/{name}.table']

        found = None
        for one in tries:
            paths = resolve(one, dbs)
            if paths:
                found = paths[0]
                break
        if not found:
            raise ValueError(f"no table file for {name} version {version}")

        try:
            self.dat = coups.table.TableFile.parse_string(found.open().read()).as_dict()
        except coups.table.ParseException:
            sys.stderr.write(f'failed to parse {found}\n')
            raise

    def select(self, flavor, quals):
        '''
        Return a simplified tablefile matching flavor and quals
        '''
        return TableFile(coups.table.simplify(self.dat, self.version, flavor, quals), self.dbs)


def product_table(name, version=None, flavor='NULL', quals=None, chain='current', dbs=None):
    '''
    Return a TableFile narrowed to a single product.

    If version is not given then an attempt will be made to load a
    chain file to resolve version (and quals) from flavor.

    Flavor must be given.

    Table and chain files are resolved against UPS "db" directories
    listed in "dbs".

    If no match is found, raise ValueError.
    '''
    if flavor and not version:
        cf = ChainFile(name, dbs=dbs)
        version,quals = cf.version_quals(flavor)

    tf = TableFileMultiFlavor(name, version, dbs=dbs)
    return tf.select(flavor, quals)
    

def dependency_graph(seed, graph=None):
    '''
    Return a graph holding seed and its dependencies.
    '''
    if graph is None:
        graph = nx.DiGraph(title=f"dependencies for {seed}")

    seed_node = str(seed)
    print(f'seeding on <{seed_node}>')
    graph.add_node(seed_node, obj=seed)
    
    def load(deps, required):
        for dep in deps:
            dependency_graph(dep, graph)
            dep_node = str(dep)
            print(f'require ({required}) <{dep_node}>')
            graph.add_edge(seed_node, dep_node, required=required)

    reqs, opts = seed.deps
    load(reqs, True)
    load(opts, False)
    return graph



def _find_product_version(pdir, version):
    '''
    Return list of version infos for the product at the path and
    specific version.

    The list consists of tuple elements (path, obj)

    The path is to the version file parsed and obj is result of
    parsing.
    '''
    pdir = Path(pdir)
    vunder = vunderify(version)

    vfile = vunder + '.version'
    vfile = pdir / vfile

    if vfile.is_dir():
        vfiles = vfile.glob("*")
    else:
        vfiles = [vfile]

    ret = list()
    for vfile in vfiles:
        if not vfile.exists():
            continue
        lines = list(vfile.open().readlines())
        try:
            vobjs = read_version(list(lines))
        except ParseException as err:
            print (vfile)
            print (''.join(lines))
            raise
        ret.append((vfile, vobjs))
    return ret


def _find_product_versions(pdir):
    '''
    Return list of version infos for the product at the path.

    The list consists of tuple elements (path, obj)

    The path is to the version file parsed and obj is result of
    parsing.
    '''
    pdir = Path(pdir)
    ret = list()
    for dotv in pdir.glob("*.version"):
        ret += _find_product_version(pdir, versionify(dotv.stem))
    return ret

def setify_quals(quals):
    if not quals:
        return set()
    if isinstance(quals,str):
        quals = quals.split(":")
    ret = set()
    for q in quals:
        q = str(q)
        if q.lower() in ("", "none", "null"):
            continue
        ret.add(q)
    return ret


def product_tuple(fdat):
    '''
    Convert a flavor data structure to product tuple
    '''
    return make_product(fdat['product'],
                        fdat['version'],
                        fdat.get('flavor', ''),
                        fdat.get('qualifiers', ''))


def find_products(name, version=None, flavor=None, quals=None, dbs=None):
    '''
    Find all products in repository paths return a list of product tuples

    If version given, reduce to matching, etc flavor, etc quals.
    '''
    version = versionify(version)
    flavor = flavor or ''
    quals = setify_quals(quals)
    pdirs = resolve(name, dbs)
    # print(f'{len(pdirs)} directories for {name}')
    vinfos = list()
    for pdir in pdirs:
        if version:
            vinfos += _find_product_version(pdir, version)
        else:
            vinfos += _find_product_versions(pdir)
    # print(f'{len(vinfos)} versions for {name}')
    ret = list()
    for vinfo in vinfos:
        vpath, vdat = vinfo
        for fdat in vdat['flavors']:
            myf = fdat['flavor']
            if myf == 'NULL': myf=''
            if flavor and myf != flavor:
                # print(f'flavor not match {myf} != {flavor}')
                continue
            qs = setify_quals(fdat['qualifiers'])
            if quals and quals != qs:
                # print (f'quals not match {qs} != {quals}')
                continue
            fdat['product'] = vdat['product']
            fdat['version'] = vdat['version']
            # print(fdat)
            ret.append(product_tuple(fdat))
    return ret



def _select_version(name, version, flavor, quals, paths):
    '''
    Return a select version info
    '''
    version = versionify(version)
    if not flavor or flavor == 'NULL':
        flavor = ''
    quals = setify_quals(quals)
    pdirs = resolve(name, paths)
    if not pdirs:
        raise ValueError(f'no package found {name}')
    for pdir in pdirs:
        # print(pdir)
        vinfos = _find_product_version(pdir, version)
        if not vinfos:
            # print(f'no vinfo for {pdir} {version}')
            continue
        for vinfo in vinfos:
            if not vinfo:
                # print(f'no such {pdir} {version}')
                continue
            vpath, vdat = vinfo
            myv = vdat['version']
            if myv != version:
                # print(f'version not match {myv} != {version}')
                continue
            for fdat in vdat['flavors']:
                myf = fdat['flavor']
                if myf == 'NULL': myf=''
                if myf != flavor:
                    # print(f'flavor not match {myf} != {flavor}')
                    continue
                qs = setify_quals(fdat['qualifiers'])
                if quals != qs:
                    # print (f'quals not match {qs} != {quals}')
                    continue
                fdat['product'] =vdat['product']
                fdat['version'] = vdat['version']
                return (vpath, fdat)
    raise ValueError(f'no match {name} {version} {flavor} {quals}')

def _base_subdir(path, paths):
    '''
    Separate path to (base, subdir) where base is in paths.
    '''
    path = Path(path)
    for p in paths:
        p = Path(p)
        try:
            return (p, path.relative_to(p))
        except ValueError:
            continue
    raise ValueError(f'unknown path: {path}')



def tarball(prod, paths=(), outdir="."):
    '''
    Product a product tar file from a product tuple, return its path.
    '''
    outdir = Path(outdir)

    tar_seeds = set()

    vpath, vdat = _select_version(prod.name, prod.version, prod.flavor, prod.quals, paths)
    tar_seeds.add(_base_subdir(vpath, paths))
    prod = product_tuple(vdat)

    inst_dir = prod_dir = resolve(vdat['prod_dir'], paths)[0]
    if not vpath.name.endswith(".version"):
        inst_dir = prod_dir / vpath.name.replace('_','-')

    if not prod_dir.exists():
        raise ValueError(f"no prod dir {prod_dir}")
    if not inst_dir.exists():
        raise ValueError(f"no inst dir {inst_dir}")

    tar_seeds.add(_base_subdir(inst_dir, paths))

    ups_dir = prod_dir / vdat['ups_dir']
    if not ups_dir.exists():
        raise ValueError(f"no ups dir {ups_dir}")

    tar_seeds.add(_base_subdir(ups_dir, paths))

    table_file = ups_dir / ( prod.name + ".table" )
    if not table_file.exists():
        raise ValueError(f"no table file {table_file}")
    #print(table_file)

    # print (tar_seeds)

    tfpath = outdir / prod.filename
    if not tfpath.parent.exists():
        os.makedirs(tfpath.parent)

    full_seeds = set([p/c for p,c in tar_seeds])
    def already_contained(p,c):
        f = p/c
        for full in full_seeds:
            try:
                rp = f.relative_to(full)
            except ValueError:
                continue
            if str(rp) == '.':
                continue
            return True
        return False


    tf = tarfile.open(str(tfpath), 'x:bz2')
    for parent, child in tar_seeds:
        if already_contained(parent, child):
            continue
        fp = parent/child
        print ('adding', parent, child)
        tf.add(str(fp), str(child))
    return tfpath
