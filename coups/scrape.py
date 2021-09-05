#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup

def manifest_url(name, version):
    return f'https://scisoft.fnal.gov/scisoft/bundles/{name}/{version}/manifest'

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
