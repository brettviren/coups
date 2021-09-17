#!/usr/bin/env python3
'''
Deal with scisoft server.

The gleened scisoft taxonomy is:

    - bundle :: a short, unqualifed name for a set of manifests

    - package :: a short, unqualifed name for a set of products

    - manifest :: a file name encoding identifiers

    - product :: a file name encoding identifiers

    - identifiers :: name, version, flavor, qualifiers, OS, CPU

    - vunder :: a version-like string in form vX_Y_Z

    - version :: a version string in form X.Y.Z

Note, coups "decodes" always to "version" internally and only
"encodes" to vunder when exporting to match scisoft expected patterns.

File contents:

    - manifest :: file contents consists of lines of product
      identifiers.

    - product :: file is a compressed tar file holding build products.

The choice for "version" vs "vunder" spelling is context dependent.

    - vunder :: URL paths under /bundles/ and /packages/

    - version :: manifest and product file names

Identifiers

    - not at all consistently applied

    - product may be named with flavor and dash-separated qualifers in
      some order OR with dashed OS-CPU

    - manifest seems consitent <flavor>-<extra>-<build> where extra
      names compiler like e20 or c7 and build names optimization
      (prof, debug or opt).

    - there is an "other" qualifier like s123 which when given tends
      to precede <extra>-<build>
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import os
import requests
from bs4 import BeautifulSoup
from coups.util import versionify, vunderify

base_url = "https://scisoft.fnal.gov/scisoft"
bundles_url = os.path.join(base_url, "bundles")
packages_url = os.path.join(base_url, "packages")

def manifest_url(name, version):
    vunder = vunderify(version)
    return os.path.join(bundles_url, name, vunder, "manifest")
def product_url(name, version):
    vunder = vunderify(version)
    return os.path.join(packages_url, name, vunder)

def get_manifest(mtp):
    '''
    Return manifest text given manifest object
    '''
    url = os.path.join(manifest_url(mtp.name, mtp.version), mtp.filename)
    return requests.get(url).text


def table(url):
    '''
    Yield URLs from rows of scisoft index page main table.
    
    Note, the overall URL hierarcy is:

      https://scisoft.fnal.gov/scisoft/bundles/<name>/<version>/manifest/<manifest>

    Where "manifest" is literal and <...>'s are iterable by this function.
    '''
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    if not soup:
        raise ValueError(f'failed to get soup from {url}')
    inner = soup.find("div", class_="inner content-inner")
    if not inner:
        raise ValueError(f'failed to get inner from {url}')
    table = inner.find("table")
    if not table:
        raise ValueError(f'failed to get table from {url}')
    rows = table.find_all("tr")
    if not rows:
        raise ValueError(f'failed to get rows from {url}')
    for row in rows:
        if not row.td:
            continue
        href = row.td.a["href"]
        yield os.path.join(page.url, href)


def path_or_directory(paths, index=None, mod=lambda x: x):
    '''
    Given a path-like string, return path or if index given just that
    element.
    '''
    if index is None:
        return paths
    for path in paths:
        if path.endswith("/"):
            path = path[:-1]
        dirs = path.split("/")
        yield mod(dirs[index])
    
def url_or_tail(url, full=True, mod=lambda x:x):
    '''
    Yield full urls or tail of urls from table at URL
    '''
    index = -1
    if full:
        index = None
    return path_or_directory(table(url), index, mod)


def bundles(full=True):
    '''
    Yield a sequence of bundle URLs.

    If full=False, yield just the bundle names
    '''
    return url_or_tail(bundles_url, full)

def bundle_versions(bundle, full=True):
    '''
    Yield a sequence of bundle version URLs

    If full=False, return just the version string. 
    Note, a version is returned and NOT a vunder.
    '''
    return url_or_tail(os.path.join(bundles_url, bundle), full, versionify)

def bundle_manifests(bundle, version, full=True):
    '''
    Yield a sequence of manifest URLs.

    If full=False, return just the manifest file name
    '''
    return url_or_tail(manifest_url(bundle, version), full)
    
                 
def packages(full=True):
    '''
    Yield a sequence of package URLs.

    If full=False, yield just the package names
    '''
    return url_or_tail(packages_url, full)


def package_versions(package, full=True):
    '''
    Yield a sequence of package version URLs

    If full=False, return just the version string. 
    Note, a version is returned and NOT a vunder.
    '''
    return url_or_tail(os.path.join(packages_url, package), full, versionify)

def package_products(package, version, full=True):
    '''
    Yield a sequence of product URLs.

    If full=False, return just the product file name
    '''
    return url_or_tail(product_url(package, version), full)
    

def download_product(prod, todir="."):
    '''
    Download product tar file.
    '''

    if not os.path.exists(todir):
        os.makedirs(todir)

    purl = product_url(prod.name, prod.version)
    furl = os.path.join(purl, prod.filename)
    targ = os.path.join(todir, prod.filename)

    with requests.get(furl, stream=True) as req:
        req.raise_for_status()
        with open(targ, 'wb') as fp:
            for chunk in req.iter_content(chunk_size=8192): 
                fp.write(chunk)
    return targ

