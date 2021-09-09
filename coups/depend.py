#!/usr/bin/env python3
'''
Functions related to processing ups depend output.
'''

# Copyright Brett Viren 2021.
# This file is part of coups which is free software distributed under
# the terms of the GNU Affero General Public License.

from collections import defaultdict, namedtuple
import networkx as nx

Entry = namedtuple('Entry', 'name vunder flavor quals parents')

def parse(text):
    '''
    Parse output text from 'ups depend'.

    Return list of Entry tuples.

    Note, due to missing information in 'ups depends', in general only
    the first entry in the returned list should be considered
    complete.
    '''
    def count_indent(line):
        for c,l in enumerate(line):
            if l.isalpha():
                return c
            
    parents = defaultdict(list)
    stack = list()
    entries = list()

    last_n = None
    for line in text.split("\n"):
        if not line:
            continue
        c = count_indent(line)
        n = c // 3
        body = line[c:]
        parts = body.split()
        pkg = parts[0]

        vunder = parts[1]
        flavor = parts[3]
        try:
            quals = parts[parts.index("-q")+1]
        except ValueError:
            quals = ""
        entries.append(Entry(pkg,vunder,flavor,quals,list()))

        #print (f'{last_n}->{n} {pkg} {stack}')

        if last_n is None:
            assert(c == 0)
            stack.append(pkg)
            last_n = n
            continue
        if n > last_n:
            child = stack[-1]
            parents[child].append(pkg)
            stack.append(pkg)
            last_n = n
            continue
        if n < last_n:
            while len(stack) > n:
                stack.pop()
            child = stack[-1]
            parents[child].append(pkg)
            stack.append(pkg)
            last_n = n
            continue
        assert n == last_n
        stack.pop()
        child = stack[-1]
        parents[child].append(pkg)
        stack.append(pkg)
    for entry in entries:
        entry.parents.extend(parents[entry.name])
    return entries

def graph(text):
    '''
    Return a directed graph from 'ups depend' output text.

    Graph is directed from child to parent.

    A child requires the parent.  A parent provides (for) the child.

    Note, this graph does not express all direct dependencies.
    '''

    entries = parse(text)

    parents=dict();
    g = nx.DiGraph()
    for entry in entries:
        for pname in entry.parents:
            g.add_edge(entry.name, pname)

    return g
