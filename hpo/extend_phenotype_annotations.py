#!/usr/bin/env python3

"""
Extend the HPO's phenotype_annotations.tab file with additional
columns and convert to csv for Excel import.

Designed for CHEO.
"""

__author__ = 'Orion Buske (buske@cs.toronto.edu)'

import os
import sys
import re
import logging
import csv

from hpo import HPO

logger = logging.getLogger(__name__)

def script(hpo_filename, annotations_filename, out_filename):
    hpo = HPO(hpo_filename)
    categories = hpo['HP:0000118'].children

    with open(annotations_filename) as ifp, \
        open(out_filename, 'w') as csvfile:
        writer = csv.writer(csvfile)

        for i, line in enumerate(ifp):
            tokens = line.rstrip('\n').split('\t')
            hpoid = tokens[4]
            term = hpo[hpoid]
            term_ancestors = term.ancestors()
            term_categories = categories.intersection(term_ancestors)
            for cat in term_categories:
                row = tokens[:5] + [term.name, cat.id, cat.name] + tokens[5:]
                writer.writerow(row)

def parse_args(args):
    from argparse import ArgumentParser
    description = __doc__.strip()

    parser = ArgumentParser(description=description)
    parser.add_argument('hpo_filename', metavar='hp.obo')
    parser.add_argument('annotations_filename', metavar='phenotype_annotations.tab')
    parser.add_argument('out_filename', metavar='outfile.csv')
    return parser.parse_args()

def main(args=sys.argv[1:]):
    args = parse_args(args)
    script(**vars(args))

if __name__ == '__main__':
    sys.exit(main())
