#!/usr/bin/env python3
'''
Utility functions
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.


# eternal mixup due to spelling versions in two ways.
def vunderify(v):
    '''
    If v is not null, return it as a vunder
    '''
    if not v or v[0] == "v":
        return v
    return "v" + v.replace(".","_")
def versionify(v):
    if not v or v[0] != "v":
        return v
    return v[1:].replace("_",".")

