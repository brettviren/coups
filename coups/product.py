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

def partition_filename(fname):
    '''
    Parse a product file name (or URL) into a Product tuple
    '''
    ext = '.tar.bz2'

    fname = os.path.basename(fname)
    if not fname.endswith(ext):
        raise ValueError(f"does not look like a product file: {fname}")
    base = fname[:-len(ext)]

    name, version, rest = base.split("-", 2)
    quals = ""
    try:
        _ = flavor2os(rest)
        flavor = rest
    except ValueError:
        chunks = rest.split("-", 2)
        OS = chunks.pop(0)
        CPU = chunks.pop(0)
        flavor = oscpu2flavor(OS,CPU) # hail mary
        if chunks:
            quals = "-".join(chunks)
    if "-" in quals:
        quals = quals.replace("-",":")
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
        base = filename[:-len(".tar.bz2")]
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
