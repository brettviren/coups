# UPS "databases" are just too damn hard to use outside of the "ups"
# program.  heart=broken.  again.


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
