#!/usr/bin/env python3
'''
Handle scisoft products 

We *always* encode a "version" not a "vunder" but we may render to a
"vunder".
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import os
import sys
from .platform import by_oscpu, by_flavor
from .util import versionify
from collections import namedtuple
from .quals import dashed as dashed_quals
from .parsing import product as parse_product

# A product tuple. All elements string.  quals is :-separated ordered list if not empty.
Product = namedtuple("Product", "name version flavor quals filename")

def check(prod, noisy=False):
    '''
    Return true if product is self consistsent, false if consistent
    except for file name.  Raise ValueError if any other inconsistency.
    Note, filenames can not be always made consistent.
    '''
    if not prod.filename:
        raise ValueError("product requires a filename")
    n,v,f,q = partition_filename(prod.filename)
    if n != prod.name:
        raise ValueError(f'product name mismatch: have:{n} file:{prod.name}')
    if v != prod.version:
        raise ValueError(f'product version mismatch: have:{v} file:{prod.version}')
    if f != prod.flavor:
        raise ValueError(f'product flavor mismatch: have:{f} file:{prod.flavor}')
    if q != prod.quals:
        raise ValueError(f'product quals mismatch: have:{q} file:{prod.quals}')
    
    fn = make_filename(prod.name, prod.version, prod.flavor, prod.quals)
    if fn != prod.filename:
        if noisy:
            sys.stderr.write(f"warning: product filename not reproduced.\n\thave:{prod.filename}\n\tmade:{fn}\n")
        return False
    return True
    
def make_filename(name, version, flavor, quals):
    '''
    Build canonical product filename.
    '''
    version = versionify(version)
    if flavor in ("", "NULL"):
        return f'{name}-{version}.tar.bz2'
    plat = by_flavor(flavor)

    if not plat.oses:
        prefix = f'{name}-{version}-{flavor}'
    else:
        OS = plat.oses[0]
        CPU = plat.cpu
        prefix = f'{name}-{version}-{OS}-{CPU}'

    quals = dashed_quals(quals)
    if quals:
        quals = '-' + quals
    return f'{prefix}{quals}.tar.bz2'


def partition_filename(fname):
    '''
    Break a product filename into its parts.

    A product tar file name is assumed to be of the form:

    <name>-<version>[-<OS>-<CPU>[-<dquals>]|-noarch].tar.bz2

    '''
    fname = os.path.basename(fname)
    pp = parse_product.parse_string(fname).product
    
    name = pp.package
    version = pp.version
    
    if 'flavor' in pp:
        flavor = pp.flavor
    else:
        plat = by_oscpu(pp.cpuos.os, pp.cpuos.cpu)
        flavor = plat.flavor
    
    if 'quals' in pp:
        quals = ':'.join([q for q in pp.quals if q != '-'])
    else:
        quals = ''

    return name, version, flavor, quals

def make(name, version, flavor=None, quals=None, filename=None):
    '''
    Create a product tuple ("ptp") with flexible args

    - name :: the product name, aka "package"
    - version :: a version or vunder
    - quals :: a set of quals as :-separated string
    - filename :: the tar filename, if none it will be generated
    '''
    version = versionify(version)

    if flavor:
        plat = by_flavor(flavor) # check that we know it
    else:
        flavor=''

    # get into canoncial form and order
    quals = dashed_quals(quals).replace('-', ':')

    noisy = False
    if not filename:
        filename = make_filename(name, version, flavor, quals)
        noisy = True

    ptp = Product(name, version, flavor, quals, filename)
    check(ptp, noisy)           # confirm consistency
    return ptp


def parse_filename(fname):
    '''
    Parse a product file name (or URL) into a Product tuple
    '''
    name, version, flavor, quals = partition_filename(fname)
    return make(name, version, flavor, quals, fname)
