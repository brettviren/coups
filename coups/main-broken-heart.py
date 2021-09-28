# UPS "databases" are just too damn hard to use outside of the "ups"
# program.  heart=broken.  again.


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

@cli.command("table-in")
@click.argument("tarfile")
@click.pass_context
def table_in(ctx, tarfile):
    '''
    Print dependencies expressed by table file in product tar files
    '''
    from coups.product import parse_filename
    from coups.ups import table_in_tar
    seed = parse_filename(tarfile)
    text = table_in_tar(tarfile)
    print(text)
