#!/usr/bin/env python3

"""
CGI script which downloads the latest Orphanet disease-gene annotations
and outputs them in an Excel-compatible TSV format.
"""

import sys
import logging
import csv

from io import StringIO
from datetime import date
from xml.etree import ElementTree as ET
from urllib.request import urlopen

DATA_URL = 'http://www.orphadata.org/data/xml/en_product6.xml'

def convert_xml_csv(infile, outfile):
    logging.info('Parsing XML...')
    tree = ET.parse(infile)
    root = tree.getroot()

    header = ['Disorder name', 'Disorder OrphaCode', 'Association type', 'Gene symbol', 'Association status', 'Gene alternate IDs']
    logging.info('Converting to CSV...')
    writer = csv.DictWriter(outfile, dialect=csv.excel_tab, fieldnames=header)
    writer.writeheader()
    for disorder in root.findall('.//Disorder'):
        disorder_name = disorder.find('Name').text
        disorder_orpha = disorder.find('OrphaCode').text
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

    logging.info('Fetching Orphanet file: {}'.format(DATA_URL))
    infile = urlopen(DATA_URL)
    outfile = StringIO()
    convert_xml_csv(infile, outfile)

    # Get number of *bytes* to be outputted as content body
    outfile.seek(0, 2)
    content_length = outfile.tell()
    outfile.seek(0, 0)

    logging.info('Outputting to CGI...')
    print("Content-Type: application/vnd.ms-excel; charset=utf-8")
    print("Content-Disposition: attachment; filename={}".format(filename))
    print("Content-Length: {}".format(content_length))
    print()


    output = outfile.getvalue()
    if (sys.stdout.encoding == 'ANSI_X3.4-1968'):
        # Fix for outputting to CGI script
        # Output UTF-8, regardless of stdouts encoding
        # Based on: http://stackoverflow.com/questions/9322410/
        sys.stdout.flush()
        sys.stdout.buffer.write(output.encode('utf-8'))
    else:
        print(output, end='')

    sys.stdout.flush()

if __name__ == '__main__':
    sys.exit(main())
