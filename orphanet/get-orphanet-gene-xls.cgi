#!/usr/bin/env python3

"""
CGI script which downloads the latest Orphanet disease-gene annotations
and outputs them in an Excel-compatible TSV format.
"""

import os
import sys
import logging
import csv

from datetime import date
from xml.etree import ElementTree as ET
from urllib.request import urlopen

DATA_URL = 'http://www.orphadata.org/data/xml/en_product6.xml'

def convert_xml_csv(infile):
    logging.info('Parsing XML...')
    tree = ET.parse(infile)
    root = tree.getroot()

    header = ['Disorder name', 'Disorder OrphaNumber', 'Association type', 'Gene symbol', 'Association status', 'Gene alternate IDs']
    logging.info('Writing data to stdout...')
    writer = csv.DictWriter(sys.stdout, dialect=csv.excel_tab, fieldnames=header)
    writer.writeheader()
    for disorder in root.findall('.//Disorder'):
        disorder_name = disorder.find('Name').text
        disorder_orpha = disorder.find('OrphaNumber').text
        for association in disorder.find('DisorderGeneAssociationList'):
            gene = association.find('Gene')
            gene_symbol = gene.find('Symbol').text
            gene_alts = set()
            for synonym in gene.findall('SynonymList/Synonym'):
                gene_alts.add(synonym.text)
            for synonym in gene.findall('ExternalReferenceList/ExternalReference/Reference'):
                gene_alts.add(synonym.text)

            status = association.find('DisorderGeneAssociationStatus/Name').text
            type = association.find('DisorderGeneAssociationType/Name').text
            row = dict(zip(header, [disorder_name, disorder_orpha, type, gene_symbol, status, ','.join(gene_alts)]))
            writer.writerow(row)

def main():
    logging.basicConfig(level='ERROR')
    filename = 'orphanet_disease-gene_{}.xls'.format(date.today())

    print("Content-Type: application/vnd.ms-excel")
    print("Content-Disposition: attachment; filename={}".format(filename))
    print()

    logging.info('Fetching Orphanet file: {}'.format(DATA_URL))
    infile = urlopen(DATA_URL)
    convert_xml_csv(infile)

if __name__ == '__main__':
    sys.exit(main())
