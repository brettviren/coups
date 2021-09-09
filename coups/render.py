#!/usr/bin/env python3
'''
Functions to render objects to strings
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from .util import vunderify


build_types = ("prof", "debug")
def separate_quals(quals):
    '''
    Given a list of quals, return a tuple.

    First element is the list of quals with the build type removed and
    second is the build type string.
    '''
    qs = list()
    bt = None
    for q in quals:
        q = str(q)
        if q in build_types:
            bt = q
        else:
            qs.append(q)
    return (qs, bt)

def build_qual(quals):
    '''
    Find and return the build qualifier.
    '''
    quals = [str(q) for q in quals]
    for q in quals:
        if q in build_types:
            return q
    raise ValueError(f'No build qual found in {quals}')

def nonbuild_qual(quals):
    '''
    Return non build quals
    '''
    bq = build_qual(quals)
    cq = compiler_qual(quals)
    nix = [bq,cq]
    ret = list()
    quals = [str(q) for q in quals]
    for qual in quals:
        if qual in nix:
            continue
        ret.append(qual)
    ret.append(cq)
    return ret


def platform_flavor(flavor):
    '''
    Return the platform code guessed from the flavor
    slf5, slf6, slf7, d14, d15, d16, d17, d18, u14, u16, u18, u20
    '''
    flavor = str(flavor)
    try:
        return platform_flavors[flavor]
    except:
        pass
    # Make this family of functions all throw same
    raise ValueError(f'No platform for flavor: {flavor}')

compiler_qual_prefix = ("c", "e")
def compiler_qual(quals):
    '''
    Find and return the compiler qualifier.
    '''
    quals = [str(q) for q in quals]
    for q in quals:
        for pre in compiler_qual_prefix:
            if q.startswith(pre):
                rest = q[len(pre):]
                try:
                    num = int(rest)
                except ValueError:
                    continue
                return q
    raise ValueError(f'No compiler qual found in {quals}')

string = str
representation = repr
def manifest_line(prod):
    '''
    Render a product object to a manifest line.
    '''
    vunder = vunderify(prod.version)

    # 0{name} 21{vunder} 37{tarball} 98{-f flavor} 125{-a q1:q2}
    ret = f'{prod.name:21}{vunder:16}{prod.filename:61}'
    flav = 'NULL'
    if prod.flavor:
        flav = str(prod.flavor)
    ret += f'-f {flav:24}'
    if isinstance(prod.quals, str):
        quals = prod.quals
    else:
        quals = ":".join([str(q) for q in prod.quals])
    if quals:
        ret += f'-q {quals}'
    return ret
