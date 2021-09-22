#!/usr/bin/env python3
'''
Handle parsing
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.


from pyparsing import *
assert __version__[0] == '3'
from pyparsing.exceptions import ParseException

# qual_literals = ["e%d"%n for n in range(

# A compiler qual is a letter in a fixed set followed by a number
# It is mapped to a version of a compiler by:
# https://scisoft.fnal.gov/scisoft/bundles/tools/buildFW
compiler_qual = Combine((Word("ec") + Word(nums)) ^ ("gcc" + Word(nums))).set_results_name("compiler")

# Manifests have a "software" qual like "s123".
software_qual = Combine(Word("s") + Word(nums)).set_results_name("software")

# A build qual what mix of optimization or debug symbols are used
build_qual = one_of("opt prof debug").set_results_name("build")

# There is another type of qual which determines some major variant of
# the software suite.  There is a wide variety including "py2" and
# "py3" or "p###b".  It's hard to be both exaustive and rigorous.
other_qual = Combine(("py" + Word(nums)) ^ (NotAny(compiler_qual + Literal("opt") + Literal ("prof") + Literal("debug") + software_qual) + Word(alphas, alphanums + '_'))).set_results_name("other")


# An OS qual is a few letters in a fixed set plus a version.
os_qual = Combine(one_of("slf sl u d") + Word(nums)).set_results_name("os")

# A CPU (aka "machine") qual is one in a fixed set.  There are
# possibly others that what are listed here, but these are all that
# are currently supported for Scisoft builds.
cpu_qual = Literal("x86_64").set_results_name("cpu")

# These two are often used together
cpuos_qual = Combine(os_qual + '-' + cpu_qual).set_results_name("cpuos")


# A set of quals separated by dashes as seen in manifest file names or
# product tar file names.
dash_quals = (
    (compiler_qual + '-' + other_qual + '-' + build_qual) ^
    (other_qual + '-' + compiler_qual + '-' + build_qual) ^
    (compiler_qual + '-' + build_qual) ^
    compiler_qual ^ 
    other_qual 
).set_results_name("quals")

# Same but colon-separated.
colon_quals = (compiler_qual + Opt(":" + other_qual) + ":" + build_qual).set_results_name("quals")

# An encoding of OS+CPU
flavor = one_of("""
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
source
noarch""").set_results_name("flavor")


#version = delimited_list(Word(nums + 'p', alphanums), delim='.', combine=True).set_results_name("version")
version = Word(nums, 'p' + '.' + alphanums).set_results_name("version")
vunder = Combine("v" + Word(nums, alphanums+'_')).set_results_name("vunder")

# A bundle is just the manifest name without version or rest
bundle = Word(alphas, alphanums + "_").set_results_name("bundle")

# A manifest file name
manifest = Combine(bundle + '-' + version + "-" + flavor + Opt('-' + dash_quals) + '_MANIFEST.txt').set_results_name("manifest")

# A package is just the product name without version or rest
package = Word(alphas, alphanums + "_").set_results_name("package")

# A product tar file naem
product = Combine(package + '-' + version + "-" + (flavor ^ cpuos_qual) + Opt('-' + dash_quals) + '.tar.bz2').set_results_name("product")


