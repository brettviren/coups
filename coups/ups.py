#!/usr/bin/env python3
'''
Handle installed UPS product area. 

We *always* encode a "version" not a "vunder" but we may render to a
"vunder".
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups.product import make as make_product
from coups.util import vunderify, versionify
from coups.table import read_version, ParseException
from coups.quals import dashed as dashed_quals

from pathlib import Path
import tarfile



def resolve(name, paths):
    '''
    Return list of pathlib.Path object by locating "name" in paths.
    '''
    ret = list()
    for path in map(Path, paths):
        maybe = path / name
        if maybe.exists():
            ret.append(maybe)
    return ret


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


def find_products(paths, name, version=None, flavor=None, quals=None):
    '''
    Find all products in repository paths return a list of product tuples

    If version given, reduce to matching, etc flavor, etc quals.
    '''
    version = versionify(version)
    flavor = flavor or ''
    quals = setify_quals(quals)
    pdirs = resolve(name, paths)
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
