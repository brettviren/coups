#!/usr/bin/env python3
'''
Sweep together all the arbitrary name chaos.
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from collections import namedtuple 


### don't use these directly, use functions of similar names defined
### below.
# This lookup translates between pairs of OS and CPU arch found in
# some UPS product tar file names to UPS flavor.  This needed in case
# a manifest line lacks an explicit "-f flavor" entry.
_oscpu2flavor = {
    # scientific linux amd64
    ("sl5","x86_64"): "Linux64bit+2.6-2.5",
    ("sl6","x86_64"): "Linux64bit+2.6-2.12",
    ("sl7","x86_64"): "Linux64bit+3.10-2.17",
    # ubuntu amd64
    ("u14","x86_64"): "Linux64bit+3.19-2.19",
    ("u16","x86_64"): "Linux64bit+4.4-2.23",
    ("u18","x86_64"): "Linux64bit+4.15-2.27",
    ("u20","x86_64"): "Linux64bit+5.4-2.31",
    #("d12","x86_64"): "Darwin+12",
    ("d12","x86_64"): "Darwin64bit+12",
    ("d13","x86_64"): "Darwin64bit+13",
    ("d14","x86_64"): "Darwin64bit+14",
    ("d15","x86_64"): "Darwin64bit+15",
    ("d16","x86_64"): "Darwin64bit+16",
    ("d17","x86_64"): "Darwin64bit+17",
    ("d18","x86_64"): "Darwin64bit+18",
    ("noarch","noarch"): "noarch",
    ("source","source"): "source",
    ('NULL', 'NULL'): 'NULL',
    ('', ''): '',
    (None, None): None,
}
_flavor2os = {
    "Linux64bit+2.6-2.5": "slf5",
    "Linux64bit+2.6-2.12": "slf6",
    "Linux64bit+3.10-2.17": "slf7",
    # note, pullProducts reverses the definitions of "arch" and
    # "platform".  What we call "platform" it calls "myarch".  In any
    # case, flavor flattens platform + architecture.
    "Linuxppc64le64bit+3.10-2.17": "slf7",
    "Linux64bit+3.19-2.19": "u14",
    "Linux64bit+4.4-2.23": "u16",
    "Linux64bit+4.15-2.27": "u18",
    "Linux64bit+5.4-2.31": "u20",
    # Another example of plat/arch degeneracy.
    "Darwin+12": "d12",
    "Darwin64bit+12": "d12",
    "Darwin64bit+13": "d13",
    "Darwin64bit+14": "d14",
    "Darwin64bit+15": "d15",
    "Darwin64bit+16": "d16",
    "Darwin64bit+17": "d17",
    "Darwin64bit+18": "d18",
    "source": "source",
    "noarch": "noarch",
}
# fixme: rationalize these lookups more, perhaps they belong in the
# DB?

def oscpu2flavor(OS, CPU):
    '''
    Try to return the flavor corresponding to OS/CPU pair
    '''
    if OS.startswith("slf"):
        OS = "sl"  + OS[3:]
    try:
        flavor = _oscpu2flavor[(OS,CPU)]
    except KeyError:
        raise ValueError(f"Unsupported OS:{OS}/CPU:{CPU}")
    return flavor

def flavor2oscpu(flavor):
    for maybe, flav in _oscpu2flavor.items():
        if flav == flavor:
            return maybe
    raise ValueError(f'unknown flavor {flavor}')

def flavor2os(flavor):
    '''
    Return the OS corresponding to flavor
    '''
    try:
        OS = _flavor2os[flavor]
    except KeyError:
        raise ValueError(f"Unsupported flavor:{flavor}")
    return OS


    
def qual_strlist(quals, delims=":-,"):
    '''
    Return list of quals from some string encoding, retaining order.

    Pass through empty qual set by returning None
    '''
    if not quals:
        return None
    if not isinstance(quals, str):
        raise ValueError("not a string")
    for delim in delims:
        if delim in quals:
            return quals.split(delim)
    return [quals]

# Hints at https://scisoft.fnal.gov/scisoft/bundles/tools/buildFW
# "build type" full quals 
quals_build = ("prof", "debug", "opt")
quals_extra_pre = "ec"

def is_build_type(qual):
    return qual in quals_build
def is_extra(qual):
    if not qual:
        return False
    if not qual[0] in quals_extra_pre:
        return False
    return qual[1:].isdigit()
def qual_type(qual):
    if is_build_type(qual):
        return "build"
    if is_extra(qual):
        return "extra"
    return "other"

def qual_types(quals):
    '''
    Interpret quals into an object of these attributes, each holding a
    tuple of quals:

        - build :: eg "prof" or "debug"

        - extra :: eg "e20", "c7"

        - other :: any not fitting above.

    This interpretation is subject to change over time as Fermilab
    blows in the wind.
    '''
    group = dict(build=list(), extra=list(), other=list())

    if isinstance(quals, str):
        quals = qual_strlist(quals)
    for qual in quals:
        group[qual_type(qual)].append(qual)

    return namedtuple("QualTypes", "build extra other")(
        tuple(group["build"]), tuple(group["extra"]), tuple(group["other"]))
