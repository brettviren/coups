#!/usr/bin/env python3
'''
Sweep all the bullshit together.
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

# Okay, so UPS is utter garbage and everything layered on top reaks a
# putrid stench of decay and corruption.  This lookup translates
# between pairs of OS and CPU arch found in some UPS product tar file
# names to UPS flavor.  This needed in case a manifest line lacks an
# explicit "-f flavor" entry.
oscpu2flavor = {
    # scientific linux amd64
    ("slf5","x86_64"): "Linux64bit+2.6-2.5",
    ("slf6","x86_64"): "Linux64bit+2.6-2.12",
    ("slf7","x86_64"): "Linux64bit+3.10-2.17",
    # ubuntu amd64
    ("u14","x86_64"): "Linux64bit+3.19-2.19",
    ("u16","x86_64"): "Linux64bit+4.4-2.23",
    ("u18","x86_64"): "Linux64bit+4.15-2.27",
    ("u20","x86_64"): "Linux64bit+5.4-2.31",
    ("noarch","noarch"): "noarch",
    ("source","source"): "source",
}
    
flavor2os = {
    "Linux64bit+2.6-2.5": "slf5",
    "Linux64bit+2.6-2.12": "slf6",
    "Linux64bit+3.10-2.17": "slf7",
    # note, pullProducts reverses the definitions of "arch" and
    # "platform".  What we call "platform" it calls "myarch".  In any
    # case, flavor flattens platform + architecture.
    "Linuxppc64le64bit+3.10-2.17": "slf7",
    "Linux64bit+3.19-2.19": "u14",
    "Linux64bit+4.4-2.23": "u16",
    "Linux64bit+4.15-2.27": "u18",
    "Linux64bit+5.4-2.31": "u20",
    # Another example of plat/arch degeneracy.
    "Darwin+12": "d12",
    "Darwin64bit+12": "d12",
    "Darwin64bit+13": "d13",
    "Darwin64bit+14": "d14",
    "Darwin64bit+15": "d15",
    "Darwin64bit+16": "d16",
    "Darwin64bit+17": "d17",
    "Darwin64bit+18": "d18",
    "source": "source",
}
    
