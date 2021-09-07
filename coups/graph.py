#!/usr/bin/env python3
'''
Build graph structure from coups objects.
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from .store import Product, Manifest
import networkx as nx

def add_object_node(g, obj):
    if isinstance(obj, Manifest):
        l = "m"
    elif isinstance(obj, Product):
        l = "p"
    else:
        raise TypeError("unknown object type: " + str(type(obj)))
    n = "%s%d" % (l, obj.id)
    g.add_node(n, obj=obj)
    return n

def from_edges(edges):
    g = nx.Graph()

    for edge in edges:
        n1 = add_object_node(g, edge[0])
        n2 = add_object_node(g, edge[1])
        g.add_edge(n1,n2)
        
    return g


    
