#!/usr/bin/env python3
'''
Handle platform names
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from collections import namedtuple 

Platform = namedtuple("Platform", "flavor cpu oses")

### don't use this directly.  perhaps they belong in a db table
platforms = [
    Platform("Linux64bit+2.6-2.5",      "x86_64", ( "slf5", "sl5")),
    Platform("Linux64bit+2.6-2.12",     "x86_64", ( "slf6", "sl6")),
    Platform("Linux64bit+3.10-2.17",    "x86_64", ( "slf7", "sl7")),
    # ubuntu amd64
    Platform("Linux64bit+3.19-2.19",    "x86_64", ( "u14",)),
    Platform("Linux64bit+4.4-2.23",     "x86_64", ( "u16",)),
    Platform("Linux64bit+4.15-2.27",    "x86_64", ( "u18",)),
    Platform("Linux64bit+5.4-2.31",     "x86_64", ( "u20",)),
    # mac
    Platform("Darwin64bit+12",          "x86_64",  ( "d12",)),
    Platform("Darwin64bit+13",          "x86_64",  ( "d13",)),
    Platform("Darwin64bit+14",          "x86_64",  ( "d14",)),
    Platform("Darwin64bit+15",          "x86_64",  ( "d15",)),
    Platform("Darwin64bit+16",          "x86_64",  ( "d16",)),
    Platform("Darwin64bit+17",          "x86_64",  ( "d17",)),
    Platform("Darwin64bit+18",          "x86_64",  ( "d18",)),
    # non-binary
    Platform("noarch", "",()),
    Platform("source", "",()),
    Platform('NULL', "", ()),
]


def by_oscpu(OS, CPU):
    '''
    Try to return the flavor corresponding to OS/CPU pair
    '''
    for p in platforms:
        if CPU == p.cpu and OS.lower() in p.oses:
            return p
    raise ValueError(f"Unsupported OS:{OS}/CPU:{CPU}")

def by_flavor(flavor):
    for p in platforms:
        if p.flavor == flavor:
            return p
    raise ValueError(f'unknown flavor {flavor}')


