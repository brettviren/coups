from coups.table import *
from pathlib import Path
import json

def dump(n, p):
    if not isinstance(p, dict):
        p = p.as_dict()
    jtext = json.dumps(p, indent=4)
    print(f'{n}:\n{jtext}')



def test_argstr():
    text = '''
(WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_(PROD)_FLAVOR}-c7-prof () )
'''
    got = ArgString.parse_string(text)
    dump("argstr", got)
    s = got.as_dict()["argstr"]
    assert "()" in s

def test_command_one():
    text = '''
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
'''
    got = COMMAND.parse_string(text)
    dump("command", got)
    d = got.as_dict()
    assert d['command'] == 'envSet'
    assert isinstance(d['argstr'], str)
    

def test_command_many():
    text = '''
    envSet1 (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
    envSet2 (ABC_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
'''
    got = Commands.parse_string(text)
    dump("commands", got)
    l = got.as_dict()["commands"]
    assert isinstance(l, list)
    assert len(l) == 2
    assert l[0]["command"] == "envSet1"
    

def test_action_blocks_1():
    text = '''
   Action=install_init_d
     Execute(${UPS_UPS_DIR}/install_init_d.sh, UPS_ENV)
'''
    got = ActionBlocks.parse_string(text)
    dump("action_blocks_1", got)


def test_action_blocks_2():
    text = '''
  action = test
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
    envSet (WIRECELL_FQ_DIR2, ${UPS_PROD_DIR}2/${UPS_PROD_FLAVOR}-c7-prof)
  action = test2
    envSet (WIRECELL_FQ_DIR, ${UPS_PROD_DIR}/${UPS_PROD_FLAVOR}-c7-prof)
    envSet (WIRECELL_FQ_DIR2, ${UPS_PROD_DIR}2/${UPS_PROD_FLAVOR}-c7-prof)
'''
    got = ActionBlocks.parse_string(text)
    dump("action_blocks_2", got)


def test_settings():
    text = '''
Foo = Bar
Blah = "string"
Meh =
    '''
    got = Settings.parse_string(text)
    dump("settings", got)
    l = got.as_dict()['settings']
    assert len(l) == 3


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
    dump("flavor_block", got)
    fb = got.as_dict()["flavorblock"]
    ab = fb['actionblocks']
    assert len(ab) == 2
    assert len(ab[1]["commands"]) == 8
    assert fb["flavor"] == "ANY"
    assert fb["qualifiers"] == "c7:prof" # quotes shoud be stripped


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
    dump("group_block", got)
    fbs = got.as_dict()["flavorblocks"]
    assert len(fbs) == 2
    assert fbs[0]["qualifiers"] == "c7:prof"
    assert fbs[1]["qualifiers"] == "c7:debug"
    assert "action" not in fbs[0] # subkeys can 'leak up' with no pp.Group()
    

def test_common():
    text = '''
Common:
   Action=install_init_d
     Execute(${UPS_UPS_DIR}/install_init_d.sh, UPS_ENV)
     setupRequired(clang v7_0_0)
End:
'''
    got = CommonBlock.parse_string(text)
    dump("common", got)
    acts = got.as_dict()["actionblocks"]
    assert len(acts) == 1
    assert len(acts[0]["commands"]) == 2


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
    dump("mixed", got)
    d = got.as_dict()
    assert d["file"].lower() == "table"
    fbs = d["flavorblocks"]
    assert len(fbs) == 1
    assert len(fbs[0]["settings"]) == 2
    actbs = d["actionblocks"]
    assert len(actbs) == 2
    assert len(actbs[1]["commands"]) == 15


def parse(What, fname):
    path = Path(__file__).parent / fname
    text = path.open().read()
    got = What.parse_string(text)
    #print(json.dumps(got.as_dict(), indent=4))
    dump(f'parse {fname}', got)
    

# I should figure out parameterized tests...
def test_parse_ups_table() : parse(TableFile, "ups.table")
def test_parse_ups_version() : parse(TableFile, "ups.version")
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
    dump(f'simp {pkg}', tdat2)
    assert fb["flavor"] == flavor
    assert fb["qualifiers"] == quals

def test_simp_afs() : simp("afs")
def test_simp_kx509() : simp("kx509")
def test_simp_wirecell() : simp("wirecell")


def test_chain():
    parse(ChainFile, "cigetcert.chain")
