#!/usr/bin/env python3
'''
Functions to render objects to strings
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from .util import vunderify
from .unko import qual_types, flavor2os

string = str
representation = repr
def manifest_line(prod):
    '''
    Render a product object to a manifest line.
    '''
    vunder = vunderify(prod.version)

    # 0{name} 21{vunder} 37{tarball} 98{-f flavor} 125{-a q1:q2}
    ret = f'{prod.name:21}{vunder:16}{prod.filename:61}'
    flav = 'NULL'
    if prod.flavor:
        flav = str(prod.flavor)
    ret += f'-f {flav:24}'
    if isinstance(prod.quals, str):
        quals = prod.quals
    else:
        quals = ":".join([str(q) for q in prod.quals])
    if quals:
        ret += f'-q {quals}'
    return ret

# name prefix for images our dockerfiles generate
default_image_prefix = "brettviren/coups-"
# which operating system to use for the base
default_operating_system = "slf7"
supported_oses = ("slf7",)

# The external base image on which we build
default_base_image = "docker.io/scientificlinux/sl:7"
# Packages to add to the base image
default_base_packages = "less curl wget tar perl redhat-lsb-core zip unzip rsync".split()
def dockerfile_base(prefix=default_image_prefix,
                    operating_system=default_operating_system,
                    from_image=default_base_image,
                    packages=default_base_packages):
    '''
    Return tuple (image name, Dockerfile text) for the base image
    '''
    if operating_system not in supported_oses:
        raise RuntimeError(f'OS {operating_system} not supported')

    pkgs = ' '.join(packages)

    # This version hard-wires the following patttern.  Since caller
    # provides from and packages, they may distinguish the image with
    # a different name or via an image name prefix.
    dfname = operating_system + "-base:0.1"
    dftext = f'''
FROM {from_image}
RUN \\
    yum -y install epel-release && \\
    yum -y install https://repo.ius.io/ius-release-el7.rpm && \\
    yum -y update && \\
    yum -y install {pkgs} && \\
    yum clean all
'''
    return prefix+dfname, dftext

def dockerfile_manifest(from_image, man,
                        prefix=default_image_prefix,
                        operating_system=default_operating_system,
                        local=False, strip=False):
    '''
    Return tuple (image name, Dockerfile text) for a manifest image

    If local is true then the Dockerfile text will assume the properly
    named manifest file is in the build context.
    '''
    flavor = str(man.flavor)
    OS = flavor2os(flavor)
    if OS != operating_system or operating_system != "slf7":
        raise RuntimeError(f'Image/manifest OS mismatch: {operating_system} != {OS} with flavor: {flavor}')

    quals = ":".join([str(q) for q in man.quals])
    qt = qual_types(quals)
    build_spec = "-".join(qt.build)
    qual_set = "-".join(qt.other + qt.extra)

    local_man=local_flag=""
    if local:
        local_flag = "-l"
        local_man = f'RUN mkdir -p /products\nCOPY {man.filename} /{man.filename}'

    local_flag = "-l" if local else ""

    stripcmd=striplab=""
    if strip:
        striplab="-strip"
        # for some reason I can not figure out, the find command to
        # remove source directories complains about them not existing,
        # yet it actually succeeds.
        stripcmd = "&& find /products -name '*.so' -print -exec strip {} \\; && find /products -name source -type d -exec rm -rf {} \\; || echo 'Ignore these errors'"


    dfname = f'{man.version}-{operating_system}-{quals}{striplab}'
    dfname = dfname.replace("+","-").replace(":","-").lower()
    dfname = prefix + man.name + ':' + dfname

    vunder = vunderify(man.version)
    dftext = f'''
FROM {from_image}
LABEL bundle="{man.name}" version="{man.version}" flavor="{man.flavor}" quals={quals}
{local_man}
RUN mkdir -p /products && \\
    curl https://scisoft.fnal.gov/scisoft/bundles/tools/pullProducts > pullProducts && \\
    chmod +x pullProducts && \\
    ./pullProducts {local_flag} -s /products {operating_system} {man.name}-{vunder} {qual_set} {build_spec} {stripcmd}
'''
    return dfname, dftext
