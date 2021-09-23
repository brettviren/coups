#!/usr/bin/env pytest
'''
Test coups.ups
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

import os
from coups import ups
from coups.quals import dashed as dashed_quals
from coups.table import TableFile
from pathlib import Path

repos = ["/cvmfs/fermilab.opensciencegrid.org/products/common/db",
         "/cvmfs/fermilab.opensciencegrid.org/products/common/prd",
         "/cvmfs/larsoft.opensciencegrid.org/products"]
os.environ['PRODUCTS'] = ":".join(repos)

def test_table_file():
    got = ups.table_file("ups", "6.1.0")
    print(repr(got))

def test_parse_ups_table_file():
    path = Path(__file__).parent / "ups.table"
    text = path.open().read()
    got = TableFile.parse_string(text)
    print(repr(got))

def _do_test_quals(qualslist, isman=False):
    nam = "manifest" if isman else "product"

    for quals in qualslist:
        qs = dashed_quals(quals, isman)
        want = quals.replace(":","-")
        print (f'{nam} {want} -> {qs}')
        assert want == qs

def test_product_quals():
    from fodder import product_qualifiers
    _do_test_quals(product_qualifiers)

def test_manifest_quals():
    from fodder import manifest_qualifiers
    _do_test_quals(manifest_qualifiers, True)    
