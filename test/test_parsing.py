#!/usr/bin/env pytest
'''
Test parsing
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import pytest
import coups.parsing as pp
from pyparsing.exceptions import ParseException
from pprint import pprint

def test_arglist():
    text='(WIRECELL_FQ_DIR, ( ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof ) )'
    NL = pp.Suppress(pp.LineEnd())
    AL = pp.Suppress("(") + pp.SkipTo(pp.Suppress(")") + NL).set_results_name("argstr")
    got = AL.parse_string(text)
    d = got.as_dict()
    argstr = d['argstr']
    assert isinstance(argstr, str)
    argstr = argstr.strip()
    assert argstr
    assert not argstr.startswith("(")
    assert argstr.endswith(")")
    print(repr(got))
    pprint(got.as_dict())


def parse(method, string):
    end = pp.StringEnd()
    return (method + end).parse_string(string)

def test_qual():
    for qs in "e20 c7 e1 c222".split():
        q = parse(pp.compiler_qual, qs)
        print(f'{qs} -> {q}')
        assert qs == q[0]
    for brok in "x22 ccc 20e".split():
        with pytest.raises (ParseException):
            q = parse(pp.compiler_qual, brok)
            print(f'{brok} -> {q}')

    for OS in "slf6 sl7 u20 d12".split():
        q = parse(pp.os_qual, OS)
        print(f'{OS} -> {q}')
        assert q[0] == OS

    for OS in "clf6 xl7 uu2 12".split():
        with pytest.raises (ParseException):
            q = parse(pp.os_qual, OS)
            print(f'{OS} -> {q}')
            print(q)

    for OS in "slfd6 d11_".split():
        with pytest.raises (ParseException):
            q = parse(pp.os_qual, OS)
            print(f'{OS} -> {q}')

    for bld in ["opt", "prof", "debug"]:
        for qs in "e20 c7 e1 c222".split():
            qb = qs + '-' + bld
            q = parse(pp.Combine(pp.compiler_qual + '-' + pp.build_qual), qb)
            print(f'{qb} -> {q}')
            assert q[0] == qb

    for CPU in ["x86_64"]:
        q = parse(pp.cpu_qual, "x86_64")
        print(f'{CPU} -> {q}')
        assert q[0] == CPU

    # note: x86 and ppc64 are actually possible CPUs, but we do not
    # yet know about them.  amd64 would have been a more appropriate
    # term to have used.
    for CPU in ["x86", "ppc64", "amd64"]:
        with pytest.raises (ParseException):
            q = parse(pp.cpu_qual, CPU)
            print(f'{CPU} -> {q}')

    q = pp.dash_quals.parse_string("e7-prof")
    print(q)
    assert q.compiler == 'e7'
    assert q.build == 'prof'

    q = pp.dash_quals.parse_string("e19-qt-debug")
    print(q)
    assert q.compiler == 'e19'
    assert q.other == 'qt'
    assert q.build == 'debug'

    q = pp.dash_quals.parse_string("s93-c2-debug")
    print(q)
    assert q.compiler == 'c2'
    assert q.other == 's93'
    assert q.build == 'debug'

    #hdf5-1.10.5-d18-x86_64-c2.tar.bz2
    q = parse(pp.dash_quals, 'c2')
    print(q)
    assert q.compiler == 'c2'



def test_flavor():
    flavors='''
Linux64bit+2.6-2.5
Linux64bit+2.6-2.12
Linux64bit+3.10-2.17
Linuxppc64le64bit+3.10-2.17
Linux64bit+3.19-2.19
Linux64bit+4.4-2.23
Linux64bit+4.15-2.27
Linux64bit+5.4-2.31
Darwin+12
Darwin64bit+12
Darwin64bit+13
Darwin64bit+14
Darwin64bit+15
Darwin64bit+16
Darwin64bit+17
Darwin64bit+18
source'''
    for flavor in [f.strip() for f in flavors.split() if f.strip()]:
        q = parse(pp.flavor, flavor)
        assert q.flavor == flavor
    
def test_version():
    # geant4-4.10.4.p03a-Linux64bit+2.6-2.12-e19-qt-debug_MANIFEST.txt

    q = parse(pp.version, "4.10.4.p03a")
    print(q)
    q = parse(pp.version, "3.9a")
    print(q)
    q = parse(pp.vunder, "v3_9a")
    print(q)

    with pytest.raises(ParseException):
        parse(pp.vunder, "3.9a")
    with pytest.raises(ParseException):
        parse(pp.version, "v3_9a")

def test_bundle():
    bundles = 'art canvas_base geant4'.split()
    for bund in bundles:
        q = pp.bundle.parse_string(bund)
        print (q)
        assert q[0] == bund

def test_manifest():
    # some select manifests
    from fodder import manifest_filenames as mans
    for man in mans:
        print (man)
        q = parse(pp.manifest, man)
        print (q)
        assert(q[0][0] == man)
    
    q = parse(pp.manifest, "art-1.13.01-Linux64bit+2.6-2.5-e7-prof_MANIFEST.txt")
    m = q.manifest
    assert m.bundle == "art"
    assert m.flavor == 'Linux64bit+2.6-2.5'
    assert m.compiler == 'e7'
    assert m.build == 'prof'

    q = parse(pp.manifest, "larsoft-09.28.02.01-Linux64bit+3.10-2.17-s112-e20-prof_MANIFEST.txt")
    m = q.manifest
    assert m.bundle == "larsoft"
    assert m.flavor == 'Linux64bit+3.10-2.17'
    assert m.compiler == 'e20'
    assert m.build == 'prof'
    assert m.other == 's112'


def test_product():
    from fodder import product_filenames as prods
    for prod in prods:
        print (prod)
        q = parse(pp.product, prod)
        print (repr(q))
        assert(q[0][0] == prod)
    
    q = parse(pp.product, "wirecell-0.16.0a-sl7-x86_64-e20-prof.tar.bz2")
    print(repr(q))
    p = q.product
    p.package == "wirecell"
    p.version == "0.16.0a"
    p.os == "sl7"
    p.compiler == "e20"
    p.build == "prof"
