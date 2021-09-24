#!/usr/bin/env python3
'''
Handle UPS table (and version) file
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups.util import vunderify, versionify
import pyparsing as pp
# print(f"pyparsing is version: {pp.__version__}")
assert pp.__version__[0] == '3'
ParseException = pp.ParseException


# Describe table and version files.  This description is determined
# emperically by looking at a sample of in-use files and thus may not
# capture all variants.  It does capture:
#
# - "old" style table file with a single flavor both with and without actions.
#
# - "new" style table files with group:/common:/end:
#
# - version files be they named like <pakcage>.version or
#   <package>.version/<flavor>_<quals>.  The two seem the same
#   internally.

DoubleQuotedString = pp.dbl_quoted_string.set_parse_action(pp.remove_quotes)

Value = pp.Word(pp.alphas, pp.alphanums + "_") ^ DoubleQuotedString
Vunder = pp.Word('v', pp.alphanums + '_')

NL = pp.Suppress(pp.LineEnd())
RestOfLine = pp.SkipTo(NL)

COMMENT = pp.Literal('#')
FILE = pp.Suppress(pp.CaselessKeyword("file") + '=') + Value('file') + NL
PRODUCT = pp.Suppress(pp.CaselessKeyword("product") + '=') + Value("product") + NL
VUNDER = pp.Suppress(pp.CaselessKeyword("version") + "=") + Vunder("vunder") + NL
CHAIN = pp.Suppress(pp.CaselessKeyword("chain") + "=") + Value("chain") + NL

GROUP = pp.Suppress(pp.CaselessKeyword("group:") + NL)
COMMON = pp.Suppress(pp.CaselessKeyword("common:") + NL)
END = pp.Suppress(pp.CaselessKeyword("end:") + NL)

# just for testing
# Header = pp.Group(FILE + PRODUCT + pp.Opt(VUNDER)).set_results_name("header").ignore('#' + pp.restOfLine)

FLAVOR = pp.Suppress(pp.CaselessKeyword("flavor") + '=') + RestOfLine('flavor') + NL
QUALIFIERS = pp.Suppress(pp.CaselessKeyword("qualifiers") + '=') + pp.Opt(DoubleQuotedString ^ '""').set_results_name('qualifiers') + NL

ACTION = pp.Suppress(pp.CaselessKeyword("action") + '=') + Value.set_results_name('action') + NL

# Command arguments can be almost arbitrary text, including
# intervening ()'s. Many seem to expect to be evaluated as shell.  So,
# here, we just punt and keep it a string
ArgString = pp.Suppress("(") + pp.SkipTo(pp.Suppress(")") + NL).set_results_name("argstr") + pp.Suppress(")") + NL

#COMMAND = pp.Group(Value.set_results_name("command") + pp.Suppress("(") + pp.ZeroOrMore(ArgList).set_results_name("arglist") + pp.Suppress(")") + NL)

COMMAND = Value.set_results_name("command") + ArgString
Commands = pp.Group(pp.ZeroOrMore(pp.Group(COMMAND))).set_results_name("commands")

ActionBlock_ = ACTION + Commands
ActionBlock = ActionBlock_.set_results_name("actionblock")
ActionBlocks = pp.Group(pp.OneOrMore(pp.Group(ActionBlock_))).set_results_name("actionblocks")


Keyname = pp.NotAny(ACTION) + pp.NotAny(FLAVOR) + pp.Word(pp.alphas, pp.alphanums + '_').set_results_name("key")
Keyvalue = RestOfLine.set_results_name("val")
Setting_ = pp.Group(Keyname + '=' + Keyvalue + NL)
Setting = Setting_.set_results_name("setting")
Settings = pp.Group(pp.OneOrMore(Setting_)).set_results_name("settings")

FlavorBlock_ = pp.Group(FLAVOR + QUALIFIERS + pp.Opt(Settings) + pp.Opt(ActionBlocks))
FlavorBlock = FlavorBlock_.set_results_name("flavorblock")

VersionBlock_ = pp.Group(FLAVOR + QUALIFIERS + Settings)
VersionBlock = VersionBlock_.set_results_name("versionblock")

ChainBlock_ = pp.Group(FLAVOR + VUNDER + QUALIFIERS + Settings)
ChainBlock = ChainBlock_.set_results_name("chainblock")

GroupBlock = GROUP + pp.ZeroOrMore(FlavorBlock_).set_results_name("flavorblocks")
CommonBlock = COMMON + ActionBlocks + END

# tantalizingly similar, but not 
TableFile = (FILE + PRODUCT + pp.Opt(VUNDER) + (GroupBlock + CommonBlock ^ FlavorBlock)).ignore('#' + pp.restOfLine)
VersionFile = FILE + PRODUCT + VUNDER + pp.ZeroOrMore(VersionBlock_).set_results_name("versionblocks")
ChainFile = FILE + PRODUCT + CHAIN + pp.ZeroOrMore(ChainBlock_).set_results_name("chainblocks")



def simplify(tdat, version, flavor, quals):
    '''
    Return a subset of tdat based on version, flavor and quals.

    For "old" table files, this will assure version, flavor and quals
    are in tdat and return it.

    For "new" table files, this will produce an "old" style tdat and
    use flavor and quals to determine which in "Group:" to apply to
    "Common:".

    The tdat is as returned by TableFile.parse_string()
    '''

    # a version file means the table need not carry a vunder
    tdat['vunder'] = vunderify(version)

    if 'flavorblock' in tdat:   # old style
        fb = tdat['flavorblock']
        fb['flavor'] = flavor
        fb['qualifiers'] = quals               
        return tdat

    # new style with group:/common:/end:

    # The main need for a version file here is to supply some things
    # which table file may (or not) leave unspecified.

    # remove these and will replace a flavorblock
    cas = tdat.pop("actionblocks") # 'Common:' actions
    fbs = tdat.pop("flavorblocks")

    # must construct a singular 'flavorblock'
    found=None
    for fb in fbs:
        if fb["qualifiers"] != quals: # fixme: order?
            continue
        if fb["flavor"] == 'ANY' or fb["flavor"] == flavor:
            found=fb
            break
    if not found:
        raise ValueError(f"No match for flavor={flavor} quals={quals}")

    genact = {a['action'].lower():a['commands'] for a in found["actionblocks"]}
    newacts = list()
    for ca in cas:
        #print(f'ca: {ca}')
        newcmds = list()
        for cmd in ca['commands']:
            # print(f'cmd: {cmd}')
            if cmd['command'].lower() in ('exeactionrequired', 'exeactionoptional'):
                al = cmd['argstr']
                # print(al)
                newcmds += genact[al.lower()]
                continue
            newcmds.append(cmd)
        newacts.append(dict(action=ca['action'], commands=newcmds))
    tdat["flavorblock"] = dict(actions=newacts, flavor=flavor, qualifiers=quals)
    return tdat

    










##########
# old parsing below.  fixme: need to purge this

def skip(lines):
    while lines:
        l = lines[0].strip()
        if not l or l.startswith("#"):
            lines.pop(0)
            continue
        return

def peek1stl(lines):
    if not lines:
        return ""
    parts = lines[0].strip().split()
    if not parts:
        return ""
    return parts[0].lower()

def read_version(lines):
    skip(lines)
    _,ftype = peek_setting(lines, key="file")
    assert ftype.lower() == "version"
    lines.pop(0)
    skip(lines)

    _,product = peek_setting(lines, key="product")
    lines.pop(0)
    skip(lines)

    _,version = peek_setting(lines, key="version")
    lines.pop(0)
    skip(lines)

    ret = dict(product=product, version=versionify(version))
    flavors = list()
    while lines:
        key, val = peek_setting(lines)
        lines.pop(0)
        skip(lines)
        if key.lower() == "flavor":
            flavors.append(dict())
        flavors[-1][key.lower()] = val
    ret["flavors"] = flavors
    return ret
    

def read_table(lines):
    skip(lines)

    _,ftype = peek_setting(lines, key="file")
    assert ftype.lower() == "table"
    lines.pop(0)

    skip(lines)

    _,product = peek_setting(lines, key="product")
    lines.pop(0)
    skip(lines)

    group = None
    if peek1stl(lines) == "group:":
        group = read_group(lines)

    common = None
    if peek1stl(lines) == "common:":
        common  = read_common(lines)

    flavor = None
    if peek1stl(lines) == "flavor:":
        flavor = read_flavor(lines)

    if len(lines) != 0:
        print(lines)

    return product,group,common,flavor

def read_group(lines):

    flavors = list()

    skip(lines)
    assert peek1stl(lines) == "group:"
    lines.pop(0)
    skip(lines)

    while lines and "common:" != peek1stl(lines):
        f = read_flavor(lines)
        flavors.append(f)
        skip(lines)

    return flavors

def peek_setting(lines, key=None):
    if not lines:
        return
    line = lines[0].strip()
    if not line:
        return

    k, v = [x.strip() for x in line.split("=",1)]
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1]

    # keyname = pp.Word(pp.alphas).set_name("key")
    # value = (pp.Word(pp.alphas) ^ pp.dbl_quoted_string).set_name("value")
    # setting = (keyname + "=" + value).set_name("setting")
    # ret = setting.parse_string(line)
    # k,v= ret[0], ret[2]

    if key and key.lower() != k.lower():
        raise ValueError(f'key constraint failed {key} != {k}')

    return k,v

def read_flavor(lines):
    ret = dict(action=list())

    while lines:
        skip(lines)
        if peek1stl(lines) in ("common:",):
            return ret

        key, val = peek_setting(lines)
        if key.lower() == "flavor" and "flavor" in ret: # next flavor
            return ret

        if key.lower() in ("flavor","qualifiers"):
            lines.pop(0)
            ret[key.lower()] = val
            continue
    
        if key.lower() == "action":
            ret['action'].append((val, read_action(lines)))
    return ret


def read_action(lines):
    assert peek1stl(lines) == "action"
    lines.pop(0)
    skip(lines)

    cmdname = pp.Word(pp.alphas).set_name("cmdname")
    # prod = pp.Word(pp.alphas).set_name("product")
    # vunder = pp.Word('v',pp.alphanums+"_").set_name("vunder")
    # quals = (pp.Word('-q', pp.alphanums+"+:") ^ ('-q' + pp.Word(pp.alphanums+"+:"))).set_name("quals")
    # args = (prod + vunder + pp.Opt(quals)).set_name("cmdargs")
    args = pp.Regex('[^),]+').set_name("args")
    arglist = pp.delimited_list(args).set_name("arglist")
    aline = (cmdname + "(" + pp.Opt(arglist) + ")").set_name("actcmd")

    ret = list()
    while lines:
        if peek1stl(lines) in ("common:","end:","flavor","action"):
            return ret
        a = aline.parse_string(lines[0])
        ret.append(a)
        lines.pop(0)
        skip(lines)
    skip(lines)
    return ret


def read_common(lines):
    assert "common:" == peek1stl(lines)
    lines.pop(0)
    skip(lines)

    ret = dict()
    while lines:
        if peek1stl(lines) == "end:":
            return ret

        _, name = peek_setting(lines, key="action")
        ret[name] = read_action(lines)
        if peek1stl(lines) in ("end:",):
            lines.pop(0)
            break

    return ret

if __name__ == '__main__':
    import sys
    fname = sys.argv[1]
    p,g,c = read_table(list(open(fname).readlines()))
    print (p)
    print (g)
    print (c)
    
