#!/usr/bin/env python3
'''
Handle scisoft manifest/bundle files
'''
import os
import requests
from collections import namedtuple

Entry = namedtuple("Entry",
                   "name vunder flavor quals filename")


b2b = dict(
    canvas = dict(bundle="canvas_base"),
    art = dict(has=["canvas"]),
    larbase = dict(has=["art"]),
    larsoft = dict(ver=["larbase"]),
    dune = dict(has=["larsoft"]),
)


def parse_prodname(name):
    '''
    Parse a product name into its parts n,v,f,q parts.
    '''
    parts = name.split("-")
    n = parts.pop(0)
    v = parts.pop(0)
    f = parts.pop(0)
    if parts:
        if parts[0][0] in "0123456789":
            f += "-" + parts.pop(0)
    q = ":".join(parts)
    return n,v,f,q


def parse_name(fname):
    '''
    Parse a manifest file name (or URL) into its parts
    '''
    fname = os.path.basename(fname)
    base = fname[:-len("_MANIFEST.txt")]

    n,v,f,q = parse_prodname(base)

    return Entry(n,v,f,q, fname)

def parse_body(text):
    '''
    Yield manifest.Entry objects parsed from manifest text.
    '''
    for line in text.split("\n"):
        parts = line.split()
        if not parts:
            continue

        try:
            name = parts.pop(0)
            vunder = parts.pop(0)
            fname = parts.pop(0)
        except IndexError as err:
            print(f'failed to parse: {line}')
            continue
        flav=""
        if len(parts) > 1:
            flav = parts[1]
        quals=""
        if len(parts) > 3:
            quals = parts[3]

        yield Entry(name, vunder, flav, quals, fname)


def load(url):
    '''
    Load manifest text from URL (web of local file).
    '''
    if "://" in url:
        return requests.get(url).text
    return open(url).read()



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


    
