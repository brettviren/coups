from coups.table import *
from pathlib import Path
from pprint import pprint
import json

def test_header():
    text = '''
# FILE=TABLE
FILE=TABLE
PRODUCT=someprod

  VERSION=v1_2_3  # this is tail comment

# this is a comment line
  # badly indented

'''
    got = Header.parse_string(text)
    print (f'got: {repr(got)}')

def test_flavor_block():
    text = '''

Flavor = ANY
Qualifiers = "c7:prof"

  Action = DefineFQ
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)

  Action = ExtraSetup
    setupRequired(spdlog v1_8_2 -q +c7:+prof)
    setupRequired(root v6_22_08d -q +c7:+p392:+prof)
    setupRequired(boost v1_75_0 -q +c7:+prof)
    setupRequired(jsoncpp v1_7_7e -q +c7:+prof)
    setupRequired(jsonnet v0_17_0a -q +c7:+prof)
    setupRequired(tbb v2021_1_1 -q +c7)
    setupRequired(hdf5 v1_12_0b -q +c7:+prof)
    setupRequired(clang v7_0_0)


'''
    got = FlavorBlock.parse_string(text)
    print(json.dumps(got.as_dict(), indent=4))

def test_group_block():
    text = '''

Group:

Flavor = ANY
Qualifiers = "c7:prof"

  Action = DefineFQ
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)

  Action = ExtraSetup
    setupRequired(spdlog v1_8_2 -q +c7:+prof)
    setupRequired(root v6_22_08d -q +c7:+p392:+prof)
    setupRequired(boost v1_75_0 -q +c7:+prof)
    setupRequired(jsoncpp v1_7_7e -q +c7:+prof)
    setupRequired(jsonnet v0_17_0a -q +c7:+prof)
    setupRequired(tbb v2021_1_1 -q +c7)
    setupRequired(hdf5 v1_12_0b -q +c7:+prof)
    setupRequired(clang v7_0_0)

Flavor = ANY
Qualifiers = "c7:debug"

  Action = DefineFQ
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-debug)

  Action = ExtraSetup
    setupRequired(spdlog v1_8_2 -q +c7:+debug)
    setupRequired(root v6_22_08d -q +c7:+p392:+debug)
    setupRequired(boost v1_75_0 -q +c7:+debug)
    setupRequired(jsoncpp v1_7_7e -q +c7:+debug)
    setupRequired(jsonnet v0_17_0a -q +c7:+debug)
    setupRequired(tbb v2021_1_1 -q +c7)
    setupRequired(hdf5 v1_12_0b -q +c7:+debug)
    setupRequired(clang v7_0_0)
Common:
'''
    got = GroupBlock.parse_string(text)
    print(json.dumps(got.as_dict(), indent=4))
    
def parse(fname):
    path = Path(__file__).parent / fname
    text = path.open().read()
    got = TableFile.parse_string(text)
    #print(json.dumps(got.as_dict(), indent=4))
    print(fname)
    pprint (got.as_dict())
    

# I should figure out parameterized tests...
def test_parse_afs_table() : parse("afs.table")
def test_parse_afs_version() : parse("afs.version")
def test_parse_kx509_table() : parse("kx509.table")
def test_parse_kx509_version() : parse("kx509.version")
def test_parse_wirecell_table() : parse("wirecell.table")
def test_parse_wirecell_version() : parse("wirecell.version")


def simp(pkg):
    tpath = Path(__file__).parent / f'{pkg}.table'
    vpath = Path(__file__).parent / f'{pkg}.version'

    tdat = TableFile.parse_string(tpath.open().read()).as_dict()
    vdat = TableFile.parse_string(vpath.open().read()).as_dict()
    version = versionify(vdat['vunder'])
    fdat = vdat['flavorblock']
    flavor = fdat['flavor']
    quals = fdat['qualifiers']

    tdat2 = simplify(tdat, version, flavor, quals)
    assert tdat2["file"].lower() == "table"
    assert "vunder" in tdat2
    fb = tdat2["flavorblock"]
    pprint(tdat2)
    assert fb["flavor"] == flavor
    assert fb["qualifiers"] == quals

def test_simp_afs() : simp("afs")
def test_simp_kx509() : simp("kx509")
def test_simp_wirecell() : simp("wirecell")

