#!/usr/bin/env pytest
'''
Test coups.product
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups.product import partition_filename, parse_filename, make, make_filename

def test_make_filenames():
    from fodder import product_filenames
    for fn in product_filenames:
        bits = partition_filename(fn)
        fn2 = make_filename(*bits)
        if fn == fn2:
            print (f'okay: {fn}')
        else:
            print (f'mismatch:\n\thave: {fn}\n\tmade: {fn2}')


def test_filename_parse_one():
    fn = "boost-1.56.0-source.tar.bz2"
    p = parse_filename(fn)
    fn2 = make_filename(p.name, p.version, p.flavor, p.quals)
    assert fn==fn2

def test_filename_parse_fodder():
    from fodder import product_filenames
    for fn in product_filenames:
        p = parse_filename(fn)
        assert p.filename == fn

