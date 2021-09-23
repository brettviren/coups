from coups.table import *
from pathlib import Path
from pprint import pprint
import json

def test_arglist():
    text = '''
(WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
'''
    got = ArgList.parse_string(text)
    print(repr(got))
    pprint(got.as_dict())
    
def test_command():
    text = '''
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
'''
    got = COMMAND.parse_string(text)
    print(repr(got))
    pprint(got.as_dict())
    
def test_action():
    text = '''
  action = test
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
    envSet (WIRECELL_FQ_DIR2, ${UPS_PROD_DIR}2/${UPS_PROD_FLAVOR}-c7-prof)
'''
    got = ActionBlocks.parse_string(text)
    print(repr(got))
    pprint(got.as_dict())

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
    print(repr(got))
    pprint(got.as_dict())

def test_setting():
    text = '''
Foo = Bar
Blah = "string"
Meh =
    '''
    got = Settings.parse_string(text)
    print(repr(got))
    pprint(got.as_dict())

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
    pprint(got.as_dict())

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
    pprint(got.as_dict())
    

def test_mixed():
    text = '''
File=Table
Product=ups
#*************************************************
# Starting Group definition
Group:
Flavor=ANY
Qualifiers=""

MAN_SOURCE_DIR=${UPS_PROD_DIR}/man/man
CATMAN_SOURCE_DIR=${UPS_PROD_DIR}/man/catman

Common:
   Action=install_init_d
     Execute(${UPS_UPS_DIR}/install_init_d.sh, UPS_ENV)

   Action=current
    #Execute( echo script is: && cat $BASH_SOURCE, NO_UPS_ENV)
    Execute( echo "Doing ups current for SETUPS_DIR ${SETUPS_DIR}" , NO_UPS_ENV)
    If( test -n "${SETUPS_DIR}" && test -w "${SETUPS_DIR}" )
     #Execute( set -x , NO_UPS_ENV)
     Execute( test -d ${SETUPS_DIR}/.old || mkdir ${SETUPS_DIR}/.old, NO_UPS_ENV)
     Execute( mv -f  ${SETUPS_DIR}/setup ${SETUPS_DIR}/setups.* ${SETUPS_DIR}/.old 2>/dev/null	, NO_UPS_ENV)
     Execute( cp ${UPS_UPS_DIR}/setups    ${SETUPS_DIR}	          , NO_UPS_ENV)
     Execute( cp ${UPS_UPS_DIR}/setups.p* ${SETUPS_DIR}	          , NO_UPS_ENV)
     Execute( cd ${SETUPS_DIR}					  , NO_UPS_ENV)
     Execute( ln -s setups  ${SETUPS_DIR}/setups.sh		  , NO_UPS_ENV)
     Execute( ln -s setups  ${SETUPS_DIR}/setups.csh		  , NO_UPS_ENV)
     Execute( ln -s setups  ${SETUPS_DIR}/setup	  		  , NO_UPS_ENV)

     # make sure there is a setups_layout scriptlet
     Execute( test -r ${SETUPS_DIR}/setups_layout || (cd ${SETUPS_DIR} && sh ${UPS_UPS_DIR}/find_layout.sh), UPS_ENV)

     # now execute it to update SETUPS_SAVE...
     Execute( /bin/bash -c ". ${SETUPS_DIR}/setups" 		, NO_UPS_ENV)

    Else()

     Execute( test -n "${SETUPS_DIR}" && echo "\\$SETUPS_DIR=${SETUPS_DIR} not writable", NO_UPS_ENV)
    EndIf( test -n "${SETUPS_DIR}" && test -w "${SETUPS_DIR}" )
End:
'''
    got = TableFile.parse_string(text);
    pprint(got.as_dict())


def parse(What, fname):
    path = Path(__file__).parent / fname
    text = path.open().read()
    got = What.parse_string(text)
    #print(json.dumps(got.as_dict(), indent=4))
    print(fname)
    pprint (got.as_dict())
    

# I should figure out parameterized tests...
def test_parse_afs_table() : parse(TableFile, "afs.table")
def test_parse_afs_version() : parse(VersionFile, "afs.version")
def test_parse_kx509_table() : parse(TableFile, "kx509.table")
def test_parse_kx509_version() : parse(VersionFile,"kx509.version")
def test_parse_wirecell_table() : parse(TableFile, "wirecell.table")
def test_parse_wirecell_version() : parse(VersionFile, "wirecell.version")


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


def test_chain():
    parse(ChainFile, "cigetcert.chain")
