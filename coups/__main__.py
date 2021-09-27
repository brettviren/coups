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
import pathlib
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

@cli.command("packages")
@click.option("--online/--no-online", default=False,
              help="Check online instead of DB")
@click.option("--missing/--no-missing", default=False,
              help="List what is online but not in our DB")
@click.pass_context
def packages(ctx, online, missing):
    '''
    List known packages
    '''
    if online or missing:
        there = set(list(coups.scisoft.packages(False)))

    if not online or missing:
        here = set(ctx.obj.names("product"))

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
    from coups.render import product_manifest as render_meth

    if output == "-":
        output="/dev/stdout"

    mtp = coups.manifest.make(name, version, flavor, quals)
    prods = coups.manifest.load(mtp)

    with open(output, "w") as fp:
        fp.write("# " + str(mtp) + "\n")
        for prod in prods:
            fp.write(render_meth(prod) + "\n")


def load_one_manifest(main, mtp, refresh):
    from coups.store import Manifest, Product

    mobj, existing = main.manifest(mtp, True)

    if existing and not refresh:
        click.echo(f'have {mobj}')
        return False

    mobj.products.clear() # correct?
    main.session.add(mobj)
                
    for ptp in coups.manifest.load(mtp):
        pobj, existing = main.product(ptp, True)
        mobj.products.append(pobj)
    main.session.commit()
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


def load_one_package(main, package, versions=(), newer=None, refresh=False):
    from coups.store import Product, Flavor, Qual

    for ver in coups.scisoft.package_versions(package, full=False):

        if versions and ver not in versions:
            continue

        if newer and ver < newer:
            print(f'reach old {ver} < {newer}')
            break

        try:
            for pfname in coups.scisoft.package_products(package, ver, False):
                pobj = main.qfirst(Product, filename=pfname)

                if pobj and not refresh:
                    click.echo(f'have {pobj}')
                    return

                try:
                    ptp = coups.product.parse_filename(pfname)
                except ValueError as err:
                    sys.stderr.write(str(err) + '\n')
                    continue

                if not pobj:
                    pobj = Product(filename=ptp.filename)
                    main.session.add(pobj)
                pobj.name = ptp.name
                pobj.version = ptp.version
                if ptp.flavor:
                    pobj.flavor = main.lookup(Flavor, name=ptp.flavor)
                else:
                    pobj.flavor = main.lookup(Flavor, name="NULL")
                pobj.quals = []
                if ptp.quals:
                    pobj.quals = [ main.lookup(Qual, name=q) for q in ptp.quals.split(":") ]
                main.commit(pobj)
                print(pobj)
            main.commit()

        except ValueError as err:
            click.echo(f"broken package: {package} {ver}")
            click.echo(err)
            continue


@cli.command("load-package")
@click.option("--newer", default=None,
              help="Only load those with versions lexically greater or equal than")
@click.option("--versions", default=None,
              help="Comma-separated list of versions to consider")
@click.option("--refresh/--no-refresh", default=False,
              help="If refresh, then will re-read existing")
@click.argument("package")
@click.pass_context
def load_package(ctx, newer, versions, package, refresh):
    '''
    Load a package of products into DB.
    '''
    if versions:
        versions = set([v for v in versions.split(',') if v])
    load_one_package(ctx.obj, package, versions, newer, refresh)

@cli.command("load-product")
@click.argument("product")
@click.pass_context
def load_product(ctx, product):
    '''
    Load a product to DB based on file name
    '''
    from coups.product import parse_filename
    from coups.store import Product
    ptp = parse_filename(product)
    print(ptp)
    #ctx.obj.lookup(Product, **ptp._asdict())



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


@cli.command("container-scisoft")
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
              type=click.Choice(["docker","podman"]),
              help="What container builder to use")
@click.option("--manifests", default="scisoft",
              type=click.Choice(["scisoft", "coups","local"]),
              help="Where manifest will be provided")
@click.option("--context", default="inline",
              type=click.Choice(["inline", "directory"]),
              help="Select Dockerfile context form")
@click.option("-P", "--prefix", default = "brettviren/coups-",
              help="Name prepended to every generated image name")
@click.option("-O", "--operating-system", default = "slf7",
              type=click.Choice(["slf7"]),
              help="OS to target")
@click.option("-S", "--strip/--no-strip", default = False,
              help="If true, run 'strip' on .so files")
@click.option("--extras", default=None,
              help="Comma-separated list bundle:number")
@click.option("-o", "--output", default=None,
              help="Output file or directory")
@click.argument("name")
@click.pass_context
def container_scisoft(ctx, quals, flavor, version, subsets, number,
                      builder, manifests, context,
                      prefix, operating_system, strip, extras, output, name):
    '''
    Produce layered container build scripts based on Scisoft.

    When exercised, the container build process will download and
    install product tar files from the Scisoft server using the usual
    "pullProducts" command.

    The "name" may be that of a bundle or it may be a manifest file
    name.  If the latter then specifying version, flavor and quals is
    optional.
    '''
    from coups.store import Manifest
    from coups.render import dockerfile_base, dockerfile_manifest
    from coups.render import product_manifest as render_meth

    if manifests == "local": manifests = "coups"
    if manifests == "coups" and context != "directory":
        sys.stderr.write("Warning: setting context to directory to accomodate coups manifests\n")
        context = "directory"
    local = manifests == "coups"

    subsets = set([s for s in subsets.split(",") if s])
    mtp = coups.manifest.make(name, version, flavor, quals)

    # who's
    theman = ctx.obj.qfirst(Manifest, **mtp._asdict())
    if not theman:
        sys.stderr.write(f'Unknown manifest: {mtp}')
        return -1
    submans = coups.queries.subsets(ctx.obj.session, theman, number)

    if extras:
        for extra in extras.split(","):
            mname,mnum = extra.split(":")
            mnum = int(mnum)
            more = coups.queries.subsets(ctx.obj.session, theman, mnum)
            submans += [m for m in more if m.name == mname]

    submans = coups.manifest.sort_submans(theman, submans)
    
    keep=list()
    for sm in submans:
        l,m,r = coups.manifest.cmp_objects(theman, sm)
        if len(m) == 0:
            continue
        keep.append(sm)
    submans = keep

    layers = list()
    layers.append(dockerfile_base(prefix, operating_system))

    for one in submans:
        prev = layers[-1][0]
        new = dockerfile_manifest(prev, one,
                                  prefix, operating_system,
                                  local, strip)
        layers.append(new)

    # lines for the rendered script
    shlines = [
        "#!/bin/bash",
        "set -e",
        "set -x",
    ]
    if output is None or output == "-":
        script = "/dev/stdout"
    else:
        script = output

    if context == "directory":
        if output is None or output == "-" or output == ".":
            outdir = "."
            script = "/dev/stdout"
        else:
            outdir = output
            script = output + ".sh"

        if not os.path.exists(outdir):
            os.makedirs(outdir)
        for ilayer, (dfname, dftext) in enumerate(layers):
            ldir = os.path.join(outdir, dfname)
            if not os.path.exists(ldir):
                os.makedirs(ldir)
            shlines += [
                f'cd {ldir} || exit -1',
                f'{builder} build -t {dfname} . || exit -1',
                'cd -\n'
            ]
            sys.stderr.write(ldir + "\n")

            dfilename = os.path.join(ldir, "Dockerfile")
            with open(dfilename, "w") as fp:
                fp.write(dftext + '\n')
            if not local or ilayer == 0:
                continue
            # provide manifest file to build context
            iman = ilayer-1
            one = submans[iman]
            mfilename = os.path.join(ldir, one.filename)
            with open(mfilename, "w") as fp:
                for p in one.products:
                    fp.write(render_meth(p) + '\n')
    # inline
    else:
        for dfname, dftext in layers:
            shlines.append("# -------------------")
            shlines.append(f'echo "building {dfname}"\n')
            shlines.append(f'cat <<EOF | {builder} build -t {dfname} -')
            shlines.append(dftext + '\nEOF\n')
            shlines.append(f'echo "{dfname} done"\n')
            shlines.append("# -------------------\n")            

    if script != "/dev/stdout":
        click.echo(script)
    open(script, "w").write('\n'.join(shlines))
    # container_scisoft

@cli.command("container-ups")
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
              type=click.Choice(["docker","podman"]),
              help="What container builder to use")
@click.option("--manifests", default="scisoft",
              type=click.Choice(["scisoft", "coups","local"]),
              help="Where manifest will be provided")
@click.option("--context", default="inline",
              type=click.Choice(["inline", "directory"]),
              help="Select Dockerfile context form")
@click.option("-P", "--prefix", default = "brettviren/coups-",
              help="Name prepended to every generated image name")
@click.option("-O", "--operating-system", default = "slf7",
              type=click.Choice(["slf7"]),
              help="OS to target")
@click.option("-S", "--strip/--no-strip", default = False,
              help="If true, run 'strip' on .so files")
@click.option("--extras", default=None,
              help="Comma-separated list bundle:number")
@click.option("-o", "--output", default=None,
              help="Output file or directory")
@click.argument("name")
@click.pass_context
def container_ups(ctx, quals, flavor, version, subsets, number,
                  builder, manifests, context,
                  prefix, operating_system, strip, extras, output, name):
    '''
    Produce layered container build scripts based on UPS.

    This produces a Docker build context directory populated with a
    Dockerfile and a number of product tar files.  The tar files will
    be downloaded from the Scisoft server or repacked from a UPS
    product area available on host running this command.

    When using the produced context, the build itself will not access
    Scisoft server nor require UPS products areas.

    The "name" gives a "seed" product name or product tar file.  If
    latter, it will be parsed for version, flavor and quals info.
    From the seed, all dependencies will be determined and their
    product tar files will be placed.  The ensemble will form a
    manifest and the whole will be used to add to the base docker
    image.
    '''
    from coups.store import Manifest
    from coups.render import dockerfile_base, dockerfile_manifest
    from coups.render import product_manifest as render_meth

    if manifests == "local": manifests = "coups"
    if manifests == "coups" and context != "directory":
        sys.stderr.write("Warning: setting context to directory to accomodate coups manifests\n")
        context = "directory"
    local = manifests == "coups"

    subsets = set([s for s in subsets.split(",") if s])
    mtp = coups.manifest.make(name, version, flavor, quals)

    # who's
    theman = ctx.obj.qfirst(Manifest, **mtp._asdict())
    if not theman:
        sys.stderr.write(f'Unknown manifest: {mtp}')
        return -1
    submans = coups.queries.subsets(ctx.obj.session, theman, number)

    if extras:
        for extra in extras.split(","):
            mname,mnum = extra.split(":")
            mnum = int(mnum)
            more = coups.queries.subsets(ctx.obj.session, theman, mnum)
            submans += [m for m in more if m.name == mname]

    submans = coups.manifest.sort_submans(theman, submans)
    
    keep=list()
    for sm in submans:
        l,m,r = coups.manifest.cmp_objects(theman, sm)
        if len(m) == 0:
            continue
        keep.append(sm)
    submans = keep

    layers = list()
    layers.append(dockerfile_base(prefix, operating_system))

    for one in submans:
        prev = layers[-1][0]
        new = dockerfile_manifest(prev, one,
                                  prefix, operating_system,
                                  local, strip)
        layers.append(new)

    # lines for the rendered script
    shlines = [
        "#!/bin/bash",
        "set -e",
        "set -x",
    ]
    if output is None or output == "-":
        script = "/dev/stdout"
    else:
        script = output

    if context == "directory":
        if output is None or output == "-" or output == ".":
            outdir = "."
            script = "/dev/stdout"
        else:
            outdir = output
            script = output + ".sh"

        if not os.path.exists(outdir):
            os.makedirs(outdir)
        for ilayer, (dfname, dftext) in enumerate(layers):
            ldir = os.path.join(outdir, dfname)
            if not os.path.exists(ldir):
                os.makedirs(ldir)
            shlines += [
                f'cd {ldir} || exit -1',
                f'{builder} build -t {dfname} . || exit -1',
                'cd -\n'
            ]
            sys.stderr.write(ldir + "\n")

            dfilename = os.path.join(ldir, "Dockerfile")
            with open(dfilename, "w") as fp:
                fp.write(dftext + '\n')
            if not local or ilayer == 0:
                continue
            # provide manifest file to build context
            iman = ilayer-1
            one = submans[iman]
            mfilename = os.path.join(ldir, one.filename)
            with open(mfilename, "w") as fp:
                for p in one.products:
                    fp.write(render_meth(p) + '\n')
    # inline
    else:
        for dfname, dftext in layers:
            shlines.append("# -------------------")
            shlines.append(f'echo "building {dfname}"\n')
            shlines.append(f'cat <<EOF | {builder} build -t {dfname} -')
            shlines.append(dftext + '\nEOF\n')
            shlines.append(f'echo "{dfname} done"\n')
            shlines.append("# -------------------\n")            

    if script != "/dev/stdout":
        click.echo(script)
    open(script, "w").write('\n'.join(shlines))


@cli.command("products")
@click.option("-r", "--render",
              default='string',
              type=click.Choice(['string','repr','manifest']),
              help="Render method")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def products(ctx, render, quals, flavor, version, name):
    '''
    List matching products
    '''
    import coups.render
    render_meth = getattr(coups.render, f'product_{render}')

    for p in coups.queries.products(ctx.obj.session,
                                    name, version, flavor, quals):
        print(render_meth(p))

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
@click.option("-r", "--render", default="string",
              type=click.Choice(["manifest", "string", "representation"]),
              help="Method to render a product to a string")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def manifests(ctx, render, quals, flavor, version, name):
    '''
    List matching manifests
    '''
    import coups.render
    from coups.manifest import wash_name
    from coups.store import Manifest
    render_meth = getattr(coups.render, f'product_{render}')

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
        for prod in man.products:
            print('\t'+render_meth(prod))


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
              help="Output file, '-' is stdout, default uses manifest file name")
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
    Output a manifest file from DB
    '''
    from coups.store import Manifest
    from coups.render import product_manifest as render_meth
    mtp = coups.manifest.make(name, version, flavor, quals)

    man = ctx.obj.qfirst(Manifest, **mtp._asdict())
    if not man:
        sys.stderr.write(f'No such manifest: {mtp}\n')

    if output is None:
        sys.stderr.write(f'Writing to {man.filename}\n')
        fp = open(man.filename, "w")
    elif output == "-":
        sys.stderr.write('Writing to stdout\n')
        fp = sys.stdout
    else:
        sys.stderr.write(f'Writing to {output}\n')
        fp = open(output, "w")

    for p in man.products:
        fp.write(render_meth(p) + '\n')
    fp.flush()
    fp.close()
    

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


@cli.command("load-deps-file")
@click.argument("dfile")
@click.pass_context
def load_deps_file(ctx, dfile):
    '''
    Load dependencies for the top package in a deps files.

    A deps file is as produced via 'ups depend'.

    For a full dependency graph, this must be repeated for every
    product as 'ups depend' trims its tree.
    '''
    text = open(dfile).read()
    ctx.obj.load_deps_text(text, True)


@cli.command("load-deps")
@click.option("--singularity", default=None,
              help="Run 'ups depend' in the named Singularity container")
@click.option("-P", "--products", multiple=True,
              help="A UPS 'products' area")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def load_deps(ctx, singularity, products,
              quals, flavor, version, name):
    '''
    Load product-level dependencies given a seed product.
    '''
    import subprocess
    from coups.store import Product
    from coups.util import vunderify

    if name.endswith(".tar.bz2"): # it is a product file name
        theprod = ctx.obj.qfirst(Product, filename=name)
    else:                       # bits and pieces
        kwds=dict(name=name)
        if version:
            kwds["version"] = versionify(version)
        if flavor:
            kwds["flavor"] = flavor
        if quals:
            kwds["quals"] = quals
        theprod = ctx.obj.lookup(Product, **kwds)
    if not theprod:
        sys.stderr.write("No seed product found")
        return -1

    setup = " && ".join([f'source {one}/setup' for one in products])
    if singularity:
        cmd=f'singularity exec --bind /cvmfs {singularity} /bin/bash -c "{setup} && ups depend %s"'
    else:
        cmd=f'/bin/bash -c "{setup} && ups depend %s"'

    def do_prod(prod):
        vunder = vunderify(prod.version)
        farg = f"-f {prod.flavor}" if prod.flavor else ""
        qarg = ":".join([str(q) for q in prod.quals]) if prod.quals else ""
        if qarg: qarg = f'-q {qarg}'
        args = f'{prod.name} {vunder} {farg} {qarg}'
        torun = cmd % args
        #print(torun)
        text = subprocess.check_output(torun, shell=True).decode()
        prods = ctx.obj.load_deps_text(text, False);
        print(f'{prod} with {len(prods)-1}')
        if len(prods) <= 1:
            return
        for prod in prods[1:]:
            do_prod(prod)
        
    do_prod(theprod)

    ctx.obj.commit()

@cli.command("load-manifest-deps")
@click.option("--singularity", default=None,
              help="Run 'ups depend' in the named Singularity container")
@click.option("-P", "--products", multiple=True,
              help="A UPS 'products' area")
@click.argument("manifest")
@click.pass_context
def load_manifest_deps(ctx, singularity, products, manifest):
    '''
    Load product-level dependencies given a seeding manifest.
    '''
    import subprocess
    from coups.store import Manifest
    from coups.util import vunderify

    setup = " && ".join([f'source {one}/setup' for one in products])
    if singularity:
        cmd=f'singularity exec --bind /cvmfs {singularity} /bin/bash -c "{setup} && ups depend %s"'
    else:
        cmd=f'/bin/bash -c "{setup} && ups depend %s"'

    def do_prod(prod):
        vunder = vunderify(prod.version)
        farg = f"-f {prod.flavor}" if prod.flavor else ""
        qarg = ":".join([str(q) for q in prod.quals]) if prod.quals else ""
        if qarg: qarg = f'-q {qarg}'
        args = f'{prod.name} {vunder} {farg} {qarg}'
        torun = cmd % args
        try:
            text = subprocess.check_output(torun, shell=True).decode()
        except subprocess.CalledProcessError as err:
            sys.stderr.write(str(err) + "\n")
            sys.stderr.write(torun + "\n")
            return
        #print(text)
        try:
            prods = ctx.obj.load_deps_text(text, False);
        except ValueError as err:
            sys.stderr.write(str(err))
            return
        print(f'{prod} with {len(prods)-1}')
        # if len(prods) <= 1:
        #     return
        # for prod in prods[1:]:
        #     do_prod(prod)
        
    mtp = ctx.obj.qfirst(Manifest, filename=manifest)
    for theprod in mtp.products:
        do_prod(theprod)

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


@cli.command("get-products")
@click.option("-o", "--outdir", default=".",
              help="Ouptut directory to place downloaded product files")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def get_products(ctx, outdir, quals, flavor, version, name):
    '''
    Product product tar files for matching products from Scisoft
    '''
    from coups.store import Product
    from coups.product import parse_filename
    from coups.scisoft import download_product

    if name.endswith(".tar.bz2"):
        ptp = parse_filename(name)
        pobj = ctx.obj.lookup(Product, **ptp._asdict())
        pobjs = [pobj]
    else:
        pobjs = ctx.obj.qall(
            Product, name=name, version=version,
            flavor=flavor, quals=quals)
    for prod in pobjs:
        if os.path.exists(prod.filename):
            sys.stderr.write(f"have {prod.filename}\n")
            continue
        fname = download_product(prod, outdir)
        sys.stderr.write(f"save {fname}\n")
        

@cli.command("find-products")
@click.option("-r", "--render", default="string",
              type=click.Choice(["manifest", "string", "representation","filename"]),
              help="Method to render a product to a string")
@click.option("-z", "--repository",
              multiple=True,
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
              help="The UPS repository directory (aka 'UPS database')")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def find_products(ctx, render, repository, quals, flavor, version, name):
    '''
    Find matching products in UPS 
    '''
    from coups.util import vunderify
    from coups import ups
    import coups.render

    meth = getattr(coups.render, f'product_{render}')
    prods = ups.find_products(repository, name, version, flavor, quals)
    for prod in prods:
        print (meth(prod))

@cli.command("pack-products")
@click.option("-z", "--repository",
              multiple=True,
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
              help="The UPS repository directory (aka 'UPS database')")
@click.option("-o", "--outdir", default=".",
              type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=pathlib.Path),
              help="Ouptut directory to place downloaded product files")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor")
@click.option("-v", "--version", default=None,
              help="Set the version")
@click.argument("name")
@click.pass_context
def pack_products(ctx, repository, outdir, quals, flavor, version, name):
    '''
    Product product tar files for matching products from UPS 
    '''
    from coups.util import vunderify
    from coups import ups

    try:
        prods = ups.find_products(repository, name, version, flavor, quals)
    except ValueError as err:
        sys.stderr.write(err + '\n')
        return -1

    for prod in prods:
        fname = coups.ups.tarball(prod, paths=repository, outdir=outdir)
        print (f'{fname}')


@cli.command("manipack")
@click.option("-z", "--repository",
              multiple=True,
              type=click.Path(file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
              envvar='COUPS_PRODUCTS',
              help="The UPS repository directory (aka 'UPS database')")
@click.option("-o", "--outdir", default=".",
              type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=pathlib.Path),
              help="Ouptut directory to place downloaded product files")
@click.option("-q", "--quals", default=None,
              help="Colon-separate list of qualifiers of seed product")
@click.option("-f", "--flavor", default=None,
              help="Platform flavor of seed product")
@click.option("-v", "--version", default=None,
              help="Version of seed product")
@click.option("-s", "--seed", default=None,
              help="Name of a product to seed the pack")
@click.option("-S", "--seed-manifest", default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=pathlib.Path),
              help="Name of a manifest of seed products")
@click.argument("manifest")
@click.pass_context
def manifest_packing(ctx, repository, outdir, 
                     quals, flavor, version,
                     seed, seed_manifest, manifest):
    '''
    Produce a "manifest pack" from a seed product and/or seed
    manifest.

    This produces a set of product tar files and their manifest file
    by following UPS dependencies.

    If given the <seed-manifest> file is read from these possible
    sources.  First one wins:

    1) local file

    2) Local coups DB

    3) Scisoft server

    The <manifest> is constructed to consist of the set of products
    which is the union of those in the <seed-manifest>, the <seed>
    product and dependencies specified as required or optional in UPS
    tables for any seed product and their dependencies.

    In forming this set, product tar files are collected into
    <outdir>.  These tar files are produced from one of the following
    sources.  First one wins:

    1) exists in <outdir>

    2) downloaded from the Scisoft server

    3) repacked as found in one of the given UPS <repository>(ies)

    The set of products is written as a manifest file to
    <outdir>/<manifest>.

    The <manifest> and its products are recorded in the local coups
    DB.
    '''
    from coups.manipack import Manipack
    
    if not manifest.endswith("_MANIFEST.txt"):
        manifest += "_MANIFEST.txt"
        click.echo(f"note: add extension: {manifest}")

    outman = outdir / manifest

    upsdbs = [pathlib.Path(p) for p in repository]
    mp = Manipack(outman, ctx.obj.session, upsdbs)
    mp.manifest_seed(seed_manifest)
    mp.product_seed(seed, version, flavor, quals)
    mp.commit()
    print (mp)

@cli.command("tarfile-dependencies")
@click.argument("tarfile")
@click.pass_context
def tarfile_dependencies(ctx, tarfile):
    '''
    Print dependencies expressed by table file in product tar files
    '''
    from coups.product import parse_filename
    from coups.ups import table_in_tar
    seed = parse_filename(tarfile)
    text = table_in_tar(tarfile)
    from coups.table import TableFile, simplify
    tdat = TableFile.parse_string(text)
    tdat = simplify(tdat, seed.version, seed.flavor, seed.quals)
    seed2, deps = ctx.obj.product_dependencies(tdat)
    print(seed)
    print(seed2)
    for dep in deps:
        print(dep)


def main():
    cli(obj=None)

if '__main__' == __name__:
    main()
