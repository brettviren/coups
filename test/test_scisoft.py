#!/usr/bin/env pytest
'''
Test coups.scisoft
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from coups.scisoft import *
import coups.product

some_products = [
    "ups-6.0.8-Linux64bit+5.4-2.31.tar.bz2"
]

def test_download(tmp_path):
    for filename in some_products:
        prod = coups.product.parse_filename(filename)
        got = coups.scisoft.download_product(prod, tmp_path)
        print (got)
        assert got.name == filename
