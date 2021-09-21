#!/usr/bin/env pytest
'''
Test coups.ups
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups import ups

def _do_test_quals(qualslist, isman=False):
    nam = "manifest" if isman else "product"

    for quals in qualslist:
        qs = ups.dashquals(quals, isman)
        want = quals.replace(":","-")
        print (f'{nam} {want} -> {qs}')
        assert want == qs

def test_product_quals():
    from fodder import product_qualifiers
    _do_test_quals(product_qualifiers)

def test_manifest_quals():
    from fodder import manifest_qualifiers
    _do_test_quals(manifest_qualifiers, True)    
