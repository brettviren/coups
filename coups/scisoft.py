#!/usr/bin/env python3
'''
Deal with scisoft server.
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

def manifest_url(name, version):
    return os.path.join(bundles_url, name, version, "manifest")

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
    return url_or_tail(manifest_url(bundle, vunderify(version)), full)
    
                 
