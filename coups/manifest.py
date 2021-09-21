#!/usr/bin/env python3
'''
Handle scisoft manifest files alone or in a bundle

We *always* encode a "version" not a "vunder" but we may render to a
"vunder".
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import os
import requests
from collections import namedtuple
from .util import versionify, vunderify
from .product import Product
from .scisoft import get_manifest

def Manifest(name, version, flavor, quals, filename):
    '''
    Create a manifest tuple ("mtp").

    This tries to apply validation so loves to throw.
    '''
    if not version:
        raise ValueError("manifest requires a version")
    version = versionify(version)
    if not flavor:
        raise ValueError("manifest requires a flavor")
    if not quals:
        # Fixme: technically, not true. Source manifests are a thing, this shoudl support eg:
        # https://scisoft.fnal.gov/scisoft/bundles/ifdh/v1_14_01/manifest/ifdh-1.14.01-source_MANIFEST.txt
        raise ValueError("manifest requires qualifiers")
    
    
    if not isinstance(quals, str):
        quals = ":".join(quals)
    if "-" in quals:
        quals = quals.replace("-",":")

    if not filename:
        raise ValueError("manifest requires a file name")

    return namedtuple("Manifest", "name version flavor quals filename")(
        name, version, flavor, quals, filename)



def parse_filename(fname):
    '''
    Parse a manifest file name (or URL) into a Manifest tuple
    '''
    fname = os.path.basename(fname)
    if not fname.endswith("_MANIFEST.txt"):
        raise ValueError(f"does not look like a manifest file: {fname}")
    base = fname[:-len("_MANIFEST.txt")]

    parts = base.split("-")
    n = parts.pop(0)
    v = parts.pop(0)
    f = parts.pop(0)
    if parts:
        # some have an internal dash followed by libc(?) version.
        if parts[0][0] in "0123456789":
            f += "-" + parts.pop(0)
    q = parts

    return Manifest(n, v, f, q, fname)


def wash_name(name, version=None, flavor=None, quals=None):
    '''
    Return name,version,flavor,quals 4-tuple.

    If name is not a manifest file name, return arguments.

    Else parse name as filename to provide defaults which any of the
    remaining non-None arguments may override.
    '''
    if name.endswith("_MANIFEST.txt"):
        entry = parse_filename(name)
        name = entry.name
        version = version or entry.version
        flavor = flavor or entry.flavor
        quals = quals or entry.quals
    return name,version,flavor,quals


def make(name, version, flavor, quals):
    '''
    Make a Manifest tuple object

    The name cane be a _MANIFEST.txt file name or it may be a bundle
    name.  
    '''
    name, version, flavor, quals = wash_name(name, version, flavor, quals)
    version = versionify(version)
    dquals = quals.replace(":","-")
    filename = f'{name}-{version}-{flavor}-{dquals}_MANIFEST.txt'
    return Manifest(name, version, flavor, quals, filename)

def parse_body(text):
    '''
    Return list of Product tuples parsed from manifest text.
    '''
    ret = list()
    for line in text.split("\n"):
        parts = line.split()
        if not parts:
            # empty line
            continue
        if parts[0].strip().startswith("#"):
            # comment
            continue

        flavor=""
        quals=""
        try:
            name = parts[0]
            version = versionify(parts[1])
            fname = parts[2]
            flavor = parts[4]
            quals = parts[6]
        except IndexError as err:
            # There is all kinds of garbage in this universe.
            pass                

        prod = Product(name, version, flavor, quals, fname)
        ret.append(prod)
    return ret


# base_url = "https://scisoft.fnal.gov/scisoft"
# def url(mf):
#     '''
#     Return a manifest URL from a Manifest tuple or a manifest file
#     name.
#     '''
#     if isinstance(mf, str):
#         mf = parse_filename(mf)

#     return os.path.join(base_url, "bundles", mf.name,
#                         vunderify(mf.version), "manifest",
#                         mf.filename)
# def loads(mf):
#     '''
#     Load manifest text from a URI which can be a URL, local file, file
#     name to check on scisoft or a manifest tuple object.
#     '''
#     if isinstance(mf, str):
#         if "://" in mf:
#             return requests.get(mf).text
#         if os.path.exists(mf):
#             return open(mf).read()
#         if mf.endswith("_MANIFEST.txt"):
#             return loads(url(mf)) # try scisoft
#     return loads(mf.filename)    # assume a manifest tuple or object


def load(mtp):
    '''
    Load manifest, return list of product.Product tuples
    '''
    if os.path.exists(mtp.filename):
        text = open(mtp.filename).read()
    else:
        text = get_manifest(mtp)
    return parse_body(text)


def cmp(man1, man2):
    '''
    Return a trio of set cardinalities:

    (man1-man2, man1 ∩ man2, man2-man1)
    '''
    s1 = set([p.id for p in man1.products])
    s2 = set([p.id for p in man2.products])
    return (len(s1-s2), len(s1.intersection(s2)), len(s2-s1))


def cmp_objects(man1, man2):
    '''
    Separate objects by set operation:

    (man1-man2, man1 ∩ man2, man2-man1)
    '''
    s1 = set(man1.products)
    s2 = set(man2.products)
    return (s1-s2, s1.intersection(s2), s2-s1)

    
def sort_submans(man, submans):
    '''
    Return the subman list sorted in order of increasing number of
    packages in common with man.
    '''
    submans = list(submans)
    submans.sort(key=lambda m: cmp(man, m)[1])
    return submans
