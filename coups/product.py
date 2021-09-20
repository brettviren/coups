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
from .unko import oscpu2flavor, flavor2os
from .util import versionify
from collections import namedtuple

from .parsing import product as parse_product

def partition_filename(fname):
    '''
    Parse a product tar file name (or URL) into a Product tuple

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
        flavor = oscpu2flavor(pp.cpuos.os, pp.cpuos.cpu)
    

    if 'quals' in pp:
        quals = ':'.join([q for q in pp.quals if q != '-'])
    else:
        quals = ''


    # parts = base.split("-")
    # name, version, rest = base.split("-", 2)
    # quals = ""
    # try:
    #     _ = flavor2os(rest)
    #     flavor = rest
    # except ValueError:
    #     chunks = rest.split("-", 2)
    #     OS = chunks.pop(0)
    #     CPU = chunks.pop(0)
    #     flavor = oscpu2flavor(OS,CPU) # hail mary
    #     if chunks:
    #         quals = "-".join(chunks)
    # if "-" in quals:
    #     quals = quals.replace("-",":")
    return name, version, flavor, quals

def Product(name, version, flavor, quals, filename):
    '''
    Create a product tuple ("ptp").

    This tries to apply validation so loves to throw.
    '''
    version = versionify(version)
    if not filename:
        # NEVER generate a product file name.  You will get it wrong.
        raise ValueError("a product tar file must be supplied")

    if quals:
        if not isinstance(quals, str):
            quals = ":".join([str(q) for q in quals])

    if not flavor:
        n,v,f,q = partition_filename(filename)
        if not quals:
            quals = q

    if "-" in quals:
        quals = quals.replace("-",":")

    return namedtuple("Product", "name version flavor quals filename")(
        name, version, flavor, quals, filename)


def parse_filename(fname):
    '''
    Parse a product file name (or URL) into a Product tuple
    '''
    name, version, flavor, quals = partition_filename(fname)
    return Product(name, version, flavor, quals, fname)
