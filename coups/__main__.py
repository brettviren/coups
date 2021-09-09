#!/usr/bin/env python3
'''
The coups CLI.
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.


import os
import sys
import click
from collections import namedtuple

import coups.manifest
import coups.scisoft
from coups.util import versionify

@click.group()
@click.option('--url',
              default='https://scisoft.fnal.gov/scisoft/',
              envvar='COUPS_URL',
              help="Base URL for scisoft collection")
@click.option("-s", "--store", 
              type=click.Path(dir_okay=False, file_okay=True,
                              resolve_path=True),
              envvar='COUPS_STORE',
              default="coups.db",
              help="The coups store")
@click.pass_context
def cli(ctx, url, store):
    '''
    coups pecks at containers for UPS products

    Copyright 2021 Brett Viren.  coups is free software and comes with
    absolutely no warranty.  License information and source code is
    available at https://github.com/brettviren/coups
    '''
    import coups.main
    ctx.obj = coups.main.Coups(store, url)


@cli.command("bundles")
@click.option("--online/--no-online", default=False,
              help="Check online instead of DB")
@click.option("--missing/--no-missing", default=False,
              help="List what is online but not in our DB")
@click.pass_context
def bundles(ctx, online, missing):
    '''
    List known bundles
    '''
    if online or missing:
        there = set(list(coups.scisoft.bundles(False)))

    if not online or missing:
        here = set(ctx.obj.names("manifest"))

    if online:
        show = there
    elif missing:
        show = there-here
    else:
        show = here
    show = list(show)
    show.sort()
    print(' '.join(show))


@cli.command("get-manifest")
@click.option("-o", "--output", default="-",
              help="Output file name")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Version")
@click.argument("name")
@click.pass_context
def get_manifest(ctx, output, quals, flavor, version, name):
    '''
    Get and parse a manifest and dump it back out.

    Name can be a bundle or a manifest file name or url.

    Result can be better formed than input or the whole mess can fail
    if input is really in bad shape.
    '''
    import coups.manifest
    import coups.render

    if output == "-":
        output="/dev/stdout"

    mtp = coups.manifest.make(name, version, flavor, quals)
    prods = coups.manifest.load(mtp)

    with open(output, "w") as fp:
        fp.write("# " + str(mtp) + "\n")
        for prod in prods:
            fp.write(coups.render.manifest_line(prod) + "\n")


def load_one_manifest(main, mtp, refresh):
    from coups.store import Manifest, Product

    mobj = main.qfirst(Manifest, **mtp._asdict())

    if mobj and not refresh:
        click.echo(f'have {mobj}')
        return False

    if mobj:
        mobj.products.clear() # correct?
    else:
        mobj = main.lookup(Manifest, **mtp._asdict())
                
    for ptp in coups.manifest.load(mtp):
        pobj = main.lookup(Product, **ptp._asdict())
        mobj.products.append(pobj)
    main.commit(mobj)
    click.echo(f'load {mobj}')    
    return True

@cli.command("load-manifest")
@click.option("--refresh/--no-refresh", default=False,
              help="If refresh, then will re-read existing")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Version")
@click.argument("name")
@click.pass_context
def load_manifest(ctx, refresh, quals, flavor, version, name):
    '''
    Load a manifest (file or URL) into db

    Name can be a bundle or a manifest file name or url.
    '''
    mtp = coups.manifest.make(name, version, flavor, quals)
    load_one_manifest(ctx.obj, mtp, refresh)


def load_one_bundle(main, bundle, versions=(), newer=None, refresh=False):
    for ver in coups.scisoft.bundle_versions(bundle, full=False):

        if versions and ver not in versions:
            continue

        if newer and ver < newer:
            print(f'reach old {ver} < {newer}')
            break

        try:
            for mfname in coups.scisoft.bundle_manifests(bundle, ver, False):
                mtp = coups.manifest.parse_filename(mfname)
                loaded = load_one_manifest(main, mtp, refresh)
                if not refresh and not loaded:
                    return
        except ValueError as err:
            click.echo(f"broken bundle: {bundle} {ver}")
            click.echo(err)
            continue


@cli.command("load-bundle")
@click.option("--refresh/--no-refresh", default=False,
              help="If refresh, then will re-read existing")
@click.option("--newer", default=None,
              help="Only load those with versions lexically greater or equal than")
@click.option("--versions", default=None,
              help="Comma-separated list of versions to consider")
@click.argument("bundle")
@click.pass_context
def load_bundle(ctx, refresh, newer, versions, bundle):
    '''
    Load a bundle of manifests into DB.

    Otherwise, if a bundle name or an unqualifed URL is given, scisoft
    will be scraped and the "newer" and "refresh" options apply.
    '''
    if versions:
        versions = set([v for v in versions.split(',') if v])
    load_one_bundle(ctx.obj, bundle, versions, newer, refresh)


@cli.command("update")
@click.pass_context
def update(ctx):
    '''
    Load any new manifests from known bundles.
    '''
    for bundle in ctx.obj.names("manifest"):
        load_one_bundle(ctx.obj, bundle)


@cli.command("remove")
@click.argument("manifests", nargs=-1)
@click.pass_context
def remove(ctx, manifests):
    '''
    Remove a manifest of the given filename.
    '''
    for manifest in manifests:
        man = ctx.obj.has_manifest(manifest)
        if not man:
            continue
        ctx.obj.remove_manifest(man)

        
@cli.command("compare")
@click.argument("manifest1")
@click.argument("manifest2")
@click.pass_context
def compare(ctx, manifest1, manifest2):
    '''
    Compare the set of products of two manifests
    '''
    if manifest1 == manifest2:
        return

    man1 = ctx.obj.has_manifest(manifest1)
    man2 = ctx.obj.has_manifest(manifest2)

    if not man1:
        print (f'missing: {manifest1}')
        return
    if not man2:
        print (f'missing: {manifest2}')
        return

    in1, inb, in2 = coups.manifest.cmp_objects(man1, man2)

    click.echo(f'only {manifest1}:')
    for one in sorted(in1, key=lambda x: x.name):
        click.echo(f'\t{one.filename}')
    click.echo('both')
    for one in sorted(inb, key=lambda x: x.name):
        click.echo(f'\t{one.filename}')
    click.echo(f'only {manifest2}:')
    for one in sorted(in2, key=lambda x: x.name):
        click.echo(f'\t{one.filename}')


@cli.command("compare-bundles")
@click.argument("bundle1")
@click.argument("bundle2")
@click.pass_context
def compare_bundles(ctx, bundle1, bundle2):
    '''
    Compare bundles
    '''
    missing = 0
    have = 0
    for man1 in ctx.obj.session.query(coups.store.Manifest).filter_by(name=bundle1).all():
        have += 1
        fname2 = bundle2 + man1.filename[len(bundle1):]
        man2 = ctx.obj.has_manifest(fname2)
        if not man2:
            #click.echo(f'missing {fname2}')
            missing += 1
            continue
        pbc = coups.manifest.cmp(man1, man2)
        click.echo(f'{pbc} {man1.filename} {man2.filename}')
    if missing:
        click.echo(f'have {have} {bundle1}, missing {missing} {bundle2}')


@cli.command("container")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Version")
@click.option("-n", "--number", default=0,
              help="Number of extra packages a subset may supply")
@click.option("-s", "--subsets", default = "",
              help="Comma-separated list of allowed bundle names ot use as subsets")
@click.option("--builder", default="docker",
              type=click.Choice(["docker","podman","dockerfile"]),
              help="What container builder to use")
@click.option("-B", "--basename", default = "brettviren/coups-",
              help="Container base name appended to every generated name")
@click.option("-S", "--strip/--no-strip", default = False,
              help="If true, run 'strip' on .so files")
@click.option("--extras", default=None,
              help="Comma-separated list bundle:number")
@click.option("-o", "--output", default=None,
              help="Output file, '-' is stdout, default is manifest file name")
@click.argument("name")
@click.pass_context
def container(ctx, quals, flavor, version, subsets, number, builder, basename, strip, extras, output, name):
    '''
    Build a layered container or emit files to build one.

    The name may be that of a bundle or it may be a manifest file
    name.  If the latter then specifying version, flavor and quals is
    optional.
    '''

    raise RuntimeError("wip: move this to render")

    from coups.store import Manifest

    subsets = set([s for s in subsets.split(",") if s])

    mtp = coups.manifest.make(name, version, flavor, quals)
    man = ctx.obj.qfirst(Manifest, **mtp._asdict())
    submans = coups.queries.subsets(ctx.obj.session, man, number)

    if extras:
        for extra in extras.split(","):
            mname,mnum = extra.split(":")
            mnum = int(mnum)
            more = coups.queries.subsets(ctx.obj.session, man, mnum)
            submans += [m for m in more if m.name == mname]

    submans = coups.manifest.sort_submans(man, submans)
    
    if subsets:
        subsets.add(mtp.name)
        # click.echo(f'restricting to sub-manifests: {subsets}')
        keep=list()
        for sm in submans:
            l,m,r = coups.manifest.cmp_objects(man, sm)
            if len(m) == 0:
                continue
            if sm.name in subsets:
                keep.append(sm)
        submans = keep

    dhpre=""
    if builder == "podman":
        dhpre = "docker://"

    base_layer_text = f'''FROM {dhpre}scientificlinux/sl:7
RUN \\
    yum -y install epel-release && \\
    yum -y install https://repo.ius.io/ius-release-el7.rpm && \\
    yum -y update && \\
    yum -y install less curl wget tar perl redhat-lsb-core zip unzip rsync && \\
    yum clean all
'''
    base_layer_name = f'{basename}base:0.1' # version refers to above df text

    layers = [(base_layer_name, base_layer_text)]
 
    stripcmd=striplab=""
    if strip:
        striplab="-strip"
        # for some reason I can not figure out, the find command to
        # remove source directories complains about them not existing,
        # yet it actually succeeds.
        stripcmd = "&& find /products -name '*.so' -print -exec strip {} \\; && find /products -name source -type d -exec rm -rf {} \\; || echo 'Ignore these errors'"

    for one in submans:
        baseimg = layers[-1][0]
        nbq = '-'.join(one.pp_nonbuild)
        layer_text = f'''FROM {baseimg}
LABEL bundle="{one.name}" version="{one.vunder}" flavor="{one.flavor}" compiler={one.pp_compiler} build={one.pp_build}
RUN mkdir -p /products && \\
    curl https://scisoft.fnal.gov/scisoft/bundles/tools/pullProducts > pullProducts && \\
    chmod +x pullProducts && \\
    ./pullProducts -s /products slf7 {one.name}-{one.vunder} {nbq} {one.pp_build} {stripcmd}
'''
        layer_name = f'{basename}{one.name}:{one.vunder}-{one.flavor}-{one.pp_compiler}-{one.pp_build}{striplab}'
        layer_name = layer_name.replace("+","-")
        layers.append((layer_name, layer_text))

    lines = []
    if builder == "dockerfile":
        for layer in layers:
            lines.append(f'# image name: {layer[0]}')
            lines.append(layer[1] + '\n')
    else:
        lines += [
            "#!/bin/bash",
            "set -e",
            "set -x",
        ]
        for layer in layers:
            lines.append("# -------------------")
            lines.append(f'echo "building {layer[0]}"\n')
            lines.append(f'cat <<EOF | {builder} build -t {layer[0]} -')
            lines.append(layer[1] + '\nEOF\n')
            lines.append(f'echo "{layer[0]} done"\n')
            lines.append("# -------------------\n")            
    dashquals = quals.replace(":", "+")
    if output is None:
        filename = f'{name}-{version}-{flavor}-{dashquals}.sh'
        click.echo(filename)
    elif output == "-":
        filename = "/dev/stdout"
    else:
        filename = output
        click.echo(filename)

    open(filename, "w").write('\n'.join(lines))


@cli.command("products")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def products(ctx, quals, flavor, version, name):
    '''
    List matching products
    '''
    for p in coups.queries.products(ctx.obj.session,
                                    name, version, flavor, quals):
        print(repr(p))

@cli.command("contains")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def contains(ctx, quals, flavor, version, name):
    '''
    List all manifests which contain matching products.
    '''
    for p in coups.queries.products(ctx.obj.session,
                                    name, version, flavor, quals):
        print (str(p.filename))
        for m in p.manifests:
            print('\t'+m.filename)

@cli.command("manifests")
@click.option("--products", default="",
              type=click.Choice(["", "manifest_line", "string", "representation"]),
              help="If products are to be printed, this sets the rendering function")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def manifests(ctx, products, quals, flavor, version, name):
    '''
    List matching manifests
    '''
    import coups.render
    from coups.manifest import wash_name
    from coups.store import Manifest

    name,version,flavor,quals = wash_name(name,version,flavor,quals)
    kwds=dict(name=name)
    if version:
        kwds["version"] = versionify(version)
    if flavor:
        kwds["flavor"] = flavor
    if quals:
        kwds["quals"] = quals
    mans = ctx.obj.qall(Manifest, **kwds)

    for man in mans:
        print (man.filename)
        if not products:
            continue
        render = getattr(coups.render, products)
        for prod in man.products:
            print('\t'+render(prod))


@cli.command("subsets")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.option("-n", "--number", default=0,
              help="Number of extra packages a subset may supply")
@click.option("--extras", default=None,
              help="Comma-separated list bundle:number")
@click.argument("name")
@click.pass_context
def subsets(ctx, quals, flavor, version, name, number, extras):
    '''
    Output subset manifest of matching manifests
    '''
    from coups.manifest import wash_name
    from coups.store import Manifest

    name,version,flavor,quals = wash_name(name,version,flavor,quals)
    kwds=dict(name=name)
    if version:
        kwds["version"] = versionify(version)
    if flavor:
        kwds["flavor"] = flavor
    if quals:
        kwds["quals"] = quals
    mans = ctx.obj.qall(Manifest, **kwds)

    for man in mans:
        print(man.filename)

        submans = coups.queries.subsets(ctx.obj.session, man, number)

        if extras:
            for extra in extras.split(","):
                mname,mnum = extra.split(":")
                mnum = int(mnum)
                more = coups.queries.subsets(ctx.obj.session, man, mnum)
                submans += [m for m in more if m.name == mname]

        submans = coups.manifest.sort_submans(man, set(submans))

        for sm in submans:
            l,m,r = coups.manifest.cmp_objects(man, sm)
            if len(m) == 0:
                continue
            report = '\t' + sm.filename

            common = len(m)
            adds = len(r)
            report += '\n\t\t'
            report += f'common:{common} adds:{adds}'
            if len(r):
                report += ' = ' + ', '.join([p.name for p in r])
            print(report)


@cli.command("manifest")
@click.option("-o", "--output", default=None,
              help="Output file, '-' is stdout, default is manifest file name")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def manifest(ctx, output, quals, flavor, version, name):
    '''
    Output matching manifest files
    '''
    name,version,flavor,quals = wash_name(name,version,flavor,quals)
    mans = coups.queries.manifests(ctx.obj.session,
                                   name, version, flavor, quals)
    for man in mans:

        if output is None:
            filename = man.filename
            click.echo(filename)
        elif output == "-":
            filename = "/dev/stdout"
        else:
            filename = output
            click.echo(filename)

        with open(filename, "w") as fp:
            for p in mans[0].products:
                fp.write(p.manifest_line + '\n')


@cli.command("dotify")
@click.option("-o", "--output", default="/dev/stdout",
              help="Output file")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.option("-t", "--type", default="product",
              help="Graph type")
@click.option("-d", "--distance", default=1,
              help="How far out to graph")
@click.argument("name")
@click.pass_context
def dotify(ctx, output, quals, flavor, version, type, distance, name):
    '''
    Emit a GraphViz dot file for a graph centered around a product.
    '''
    import matplotlib.pyplot as plt
    import networkx as nx

    if type.startswith("prod"):
        seeder = coups.queries.products
        grapher = getattr(ctx.obj, "graph_product")
    elif type.startswith("man"):
        seeder = coups.queries.manifests
        grapher = getattr(ctx.obj, "graph_manifest")
    else:
        click.echo(f'Unknown graph type: {type}')
        return

    g = grapher(name, version, flavor, quals, distance)
    print('graph with %d nodes' % (len(g),))
    nodes = list(g.nodes)
    colors = list()
    shapes = list()
    labels = dict()
    for n in g.nodes:
        o = g.nodes[n]["obj"]
        if n[0] == 'm':
            colors.append("red")
            shapes.append("s")
        else:
            colors.append("blue")
            shapes.append("o")        
        L = n[0].upper()
        labels[n] = f'{L}: {o.name}\n{o.vunder}'

    #pos = nx.spring_layout(g, k=0.01)
    pos = nx.nx_agraph.graphviz_layout(g, prog="neato")
    #pos = nx.circular_layout(g, scale=20)
    plt.figure(figsize=(20,20))
    nx.draw_networkx(g, pos, node_size=10, nodelist=nodes, node_color=colors, labels=labels)
    plt.savefig(output)


@cli.command("load-deps")
@click.argument("dfile")
@click.pass_context
def load_deps(ctx, dfile):
    '''
    Load dependencies for the top package in a deps files.

    A deps file is as produced via 'ups depend'.

    For a full dependency graph, this must be repeated for every
    product as 'ups depend' trims its tree.
    '''
    text = open(dfile).read()
    ctx.obj.load_deps_text(text, True)

@cli.command("load-manifest-deps")
@click.option("--prefix", default="ups depend",
              help="The command to run to get the 'ups depend' text")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def load_manifest_deps(ctx, prefix, quals, flavor, version, name):
    '''
    Load dependencies for packages listed in a manifest.

    This runs 'ups depend' as given by the --prefix option.

    The prefix may contain a '%s' which will be filled in with
    'ups depend' arguments.  Else they are appended.

    pro tip:
    --prefix='singularity exec --bind /cvmfs sl7.sif /bin/bash -c "source /cvmfs/larsoft.opensciencegrid.org/products/setup && ups depend %s"'
    
    '''
    import subprocess
    name,version,flavor,quals = wash_name(name,version,flavor,quals)
    mans = coups.queries.manifests(ctx.obj.session,
                                   name, version, flavor, quals)

    for man in mans:
        for prod in man.products:
            quals = [str(q) for q in prod.quals]
            quals.sort()
            quals = ":".join(quals) # fixme this should be in Product!
            if quals:
                quals = "-q " + quals
            flav = str(prod.flavor)
            if flav:
                flav = "-f " + flav
            args = f'{prod.name} {prod.vunder} {flav} {quals}'
            if '%' in prefix:
                cmd = prefix % (args)
            else:
                cmd = prefix + ' ' + args
            print (cmd)
            text = subprocess.check_output(cmd, shell=True).decode()
            ctx.obj.load_deps_text(text, False)
    ctx.obj.commit()


@cli.command("depend-graph")
@click.argument("dfile")
@click.pass_context
def depend_graph(ctx, dfile):
    '''
    Parse output of "ups depend <prod> <vunder> -q <quals>"
    '''
    from coups import depend
    import matplotlib.pyplot as plt
    import networkx as nx

    g = depend.graph(open(dfile).read())
    plt.figure(figsize=(50,20))
    pos = nx.nx_agraph.graphviz_layout(g, prog="dot")
    nx.draw_networkx(g, pos)
    plt.savefig(dfile + ".png")


def main():
    cli(obj=None)

if '__main__' == __name__:
    main()
