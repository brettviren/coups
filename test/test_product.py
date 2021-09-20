#!/usr/bin/env pytest
'''
Test coups.product
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups.product import parse_filename

def test_filename_parse():
    from fodder import product_filenames
    for fn in product_filenames:
        p = parse_filename(fn)
        assert p.filename == fn
