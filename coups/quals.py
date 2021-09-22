#!/usr/bin/env python3
'''
Handle qualifiers
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

# Hints at https://scisoft.fnal.gov/scisoft/bundles/tools/buildFW

from collections import namedtuple
from .parsing import software_qual, compiler_qual, build_qual, other_qual, ParseException

def types(quals):
    '''
    Interpret quals into an object of these attributes, each holding a
    tuple of quals:

        - b (build) :: eg "prof" or "debug"

        - c (compiler) :: eg "e20", "c7"

        - s (software) :: eg s123

        - o (other) :: any not fitting above.

    This interpretation is subject to change over time as Fermilab
    blows in the wind.
    '''
    b=c=s=o=''
    if not quals:
        return group
    if isinstance(quals, str):
        quals = quals.split(":")
    quals = [q for q in quals if q]

    for q in quals:
        try:
            software_qual.parse_string(q)
        except ParseException:
            pass
        else:
            s = q
            continue
        try:
            compiler_qual.parse_string(q)
        except ParseException:
            pass
        else:
            c = q
            continue
        try:
            build_qual.parse_string(q)
        except ParseException:
            pass
        else:
            b = q
            continue
        try:
            other_qual.parse_string(q)
        except ParseException:
            pass
        else:
            o = q
            continue

    return namedtuple("QualTypes", "b c s o")(b,c,s,o)

def dashed(quals, isman=False):
    '''
    Given quals, return canonical dash order.

    products: <compiler>[-<other>][-<build>]

    manifests: [<software>-]<compiler>[-<other>][-<build>]
    '''
    if not quals:
        return ''
    if isinstance(quals, str):
        quals = quals.split(":")
    quals = [q for q in quals if q]
    if len(quals) == 1:
        return quals[0]
    qt = types(quals)
    if isman:
        got = [qt.s, qt.c, qt.o, qt.b]
    else:
        got = [qt.c, qt.s, qt.o, qt.b]
    return '-'.join([q for q in got if q])

