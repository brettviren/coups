#!/usr/bin/env python3
'''
Handle UPS table (and version) file

# line oriented, case insensitive, implicitly blocked by keywords
FILE = TABLE|VERSION
PRODUCT=<name>
VERSION=<vunder>
# starts "flavor" block
FLAVOR = <flavor>
# can be empty
QUALIFIERS = "foo:bar"
ACTION = SETUP
  # non-ACTION lines body of SETUP
ACTION = OTHER
  # non-ACTION lines body of OTHER
#...
# EOF

Or, 

File = table|version
Product=<name>
Version=<vunder>

Group:

Flavor = <name>
Qualifiers = "..."
Action = <name>
  # commands
Action = <name>
  # commands

Flavor = <name>
Qualifiers = "..."
Action = <name>
  # commands
Action = <name>
  # commands

Common: # applies to each action flavor in group

Action = setup
  # commands
  exeActionRequired(<name-from-flavor-in-group>)
Action = <name>
  # commands
  exeActionRequired(<name-from-flavor-in-group>)

End: # of group
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups.util import vunderify, versionify
import pyparsing as pp
# print(f"pyparsing is version: {pp.__version__}")
assert pp.__version__[0] == '3'
ParseException = pp.ParseException

Value = pp.Word(pp.alphas, pp.alphanums) ^ pp.dbl_quoted_string.set_parse_action(pp.remove_quotes)
Vunder = pp.Word('v', pp.alphanums + '_')

NL = pp.Suppress(pp.LineEnd())
COMMENT = pp.Literal('#')
FILE = pp.Suppress(pp.CaselessKeyword("file") + '=') + Value('file') + NL
PRODUCT = pp.Suppress(pp.CaselessKeyword("product") + '=') + Value("product") + NL
VUNDER = pp.Suppress(pp.CaselessKeyword("version") + "=") + Vunder("vunder") + NL
Header = pp.Group(FILE + PRODUCT + pp.Opt(VUNDER)).ignore('#' + pp.restOfLine)


FLAVOR = pp.Suppress(pp.CaselessKeyword("flavor") + '=') + Value('flavor') + NL
QUALIFIERS = pp.Suppress(pp.CaselessKeyword("qualifiers") + '=') + pp.dbl_quoted_string('quals') + NL

ACTION = pp.Suppress(pp.CaselessKeyword("action") + '=') + Value('action') + NL
onearg = pp.Regex('[^),]+')
ArgList = pp.delimited_list(onearg)
COMMAND = pp.Group(Value.set_results_name("command") + pp.Suppress("(") + pp.ZeroOrMore(ArgList).set_results_name("arglist") + pp.Suppress(")") + NL)
ActionBlock = pp.Group(ACTION + pp.OneOrMore(COMMAND).set_results_name("commands"))

FlavorBlock_ = pp.Group(FLAVOR + QUALIFIERS + pp.ZeroOrMore(ActionBlock).set_results_name("actions"))
FlavorBlock = FlavorBlock_.set_results_name("flavorblock")

GROUP = pp.Suppress(pp.CaselessKeyword("group:") + NL)

GroupBlock = GROUP + pp.ZeroOrMore(FlavorBlock_).set_results_name("flavorblocks")

COMMON = pp.Suppress(pp.CaselessKeyword("common:") + NL)
END = pp.Suppress(pp.CaselessKeyword("end:") + NL)

CommonBlock = COMMON + pp.ZeroOrMore(ActionBlock).set_results_name("commonactions") + END

TableFile = FILE + PRODUCT + GroupBlock + CommonBlock


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
    
