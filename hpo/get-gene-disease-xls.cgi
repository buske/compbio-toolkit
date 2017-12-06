#!/usr/bin/env python3

"""
CGI script which downloads the latest HPO gene-disease and gene-inheritance annotations
and outputs them in an Excel-compatible TSV format.
"""

import sys
import logging
import csv
import codecs

from collections import defaultdict
from io import StringIO
from datetime import date
from urllib.request import urlopen

DELIM = ';'
DELIM_REPLACEMENT = ','  # if DELIM exists in one of the names

GENE2DISEASE_URL = 'http://compbio.charite.de/jenkins/job/hpo.annotations.monthly/lastStableBuild/artifact/annotation/genes_to_diseases.txt'
DISEASE2PHENOTYPE_URL = 'http://compbio.charite.de/jenkins/job/hpo.annotations/lastStableBuild/artifact/misc/phenotype_annotation.tab'

MODES_OF_INHERITANCE = {
    'HP:0000006': 'AD',
    'HP:0000007': 'AR',
    'HP:0001417': 'XL',
    'HP:0001419': 'XL-R',
    'HP:0001423': 'XL-D',
    'HP:0001425': 'Heterogeneous',
    'HP:0001426': 'Multifactorial inheritance',
    'HP:0001427': 'MT',
    'HP:0001428': 'Somatic mutation',
    'HP:0001442': 'Somatic mosaicism',
    'HP:0001444': 'Autosomal dominant somatic cell mutation',
    'HP:0001450': 'YL',
    'HP:0001452': 'Autosomal dominant contiguous gene syndrome',
    'HP:0001466': 'Contiguous gene syndrome',
    'HP:0001470': 'Sex-limited autosomal dominant',
    'HP:0001472': 'Familial predisposition',
    'HP:0001475': 'Male-limited autosomal dominant',
    'HP:0003743': 'Genetic anticipation',
    'HP:0003744': 'Genetic anticipation with paternal anticipation bias',
    'HP:0003745': 'Sporadic',
    'HP:0010982': 'Polygenic inheritance',
    'HP:0010984': 'Digenic inheritance',
    'HP:0012275': 'Autosomal dominant inheritance with maternal imprinting',
    'HP:0025352': 'Autosomal dominant germline de novo mutation',
}


def iter_remote_text_file(url):
    with urlopen(url) as resource:
        charset = resource.headers.get_content_charset() or 'utf-8'
        for line in codecs.iterdecode(resource, charset):
            yield line


def get_gene_to_disease_map():
    """
    Input file format
    #Format: entrez-gene-id<tab>entrez-gene-symbol<tab>DiseaseId
    2       A2M     OMIM:614036
    16      AARS    OMIM:616339
    16      AARS    ORPHA:442835

    Output dict:
    gene symbol -> [disease identifier, ...]
    """
    gene_diseases = defaultdict(list)

    for line in iter_remote_text_file(GENE2DISEASE_URL):
        if line.startswith('#'):
            continue

        line = line.strip()
        symbol, disease = line.split('\t')[1:3]
        assert disease not in gene_diseases[symbol]
        gene_diseases[symbol].append(disease)

    return gene_diseases

def get_disease_data():
    """
    Input file format:
    1   DB
    2   Disease ID
    3   Disease Name
    5   HPO ID
    11  Aspect  I

    Output two dicts:
    1. disease id -> disease name
    2. disease id -> [disease inheritance, ...]
    """
    disease_names = {}
    disease_inheritances = defaultdict(list)
    for line in iter_remote_text_file(DISEASE2PHENOTYPE_URL):
        try:
            line = line.strip()
            tokens = line.split('\t')
            aspect = tokens[10]
            if len(aspect) != 1:
                logging.warning('Unexpected aspect: {!r} on line: {!r}'.format(aspect, line))
                continue

            disease_id = '{}:{}'.format(tokens[0], tokens[1])
            disease_name = tokens[2]
            term_id = tokens[4]

            # Save disease name (overwrite, because why not)
            disease_names[disease_id] = disease_name

            # Skip inheritance if not inheritance aspect
            if aspect != 'I':
                continue

            # Try to resolve to human-readable inheritance
            inheritance = MODES_OF_INHERITANCE.get(term_id, term_id)
            if inheritance not in disease_inheritances[disease_id]:
                disease_inheritances[disease_id].append(inheritance)
        except:
            logging.error('Encountered error parsing disease-phenotype file at line: {!r}'.format(line))
            raise

    return disease_names, disease_inheritances


def write_mapping(gene_diseases, disease_names, disease_inheritances, outfile):
    header = ['Gene symbol', 'Disease IDs', 'Disease names', 'Modes of inheritance']
    writer = csv.DictWriter(outfile, dialect=csv.excel_tab, fieldnames=header)
    writer.writeheader()
    for gene in sorted(gene_diseases):
        disease_ids = sorted(gene_diseases[gene])
        names = sorted(set([disease_names.get(disease_id, disease_id).replace(DELIM, DELIM_REPLACEMENT) for disease_id in disease_ids]))
        inheritances = sorted(set([inheritance.replace(DELIM, DELIM_REPLACEMENT) for disease_id in disease_ids for inheritance in disease_inheritances[disease_id]]))

        row = dict(zip(header, [gene, DELIM.join(disease_ids), DELIM.join(names), DELIM.join(inheritances)]))
        writer.writerow(row)


def main():
    logging.basicConfig(level='INFO')
    filename = 'gene-disease_{}.xls'.format(date.today())

    logging.info('Fetching gene-disease mappings: {}'.format(GENE2DISEASE_URL))
    gene_diseases = get_gene_to_disease_map()
    logging.info('Fetching disease-phenotype mappings: {}'.format(DISEASE2PHENOTYPE_URL))
    disease_names, disease_inheritances = get_disease_data()

    logging.info('Generating output data...')
    outfile = StringIO()
    write_mapping(gene_diseases, disease_names, disease_inheritances, outfile)

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
