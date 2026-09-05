"""Summarize one numeric CSV column; UTF-8, comma-delimited, header required."""
import argparse
import csv
import json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('file')
p.add_argument('column')
p.add_argument('--precision', type=int, help='round total to this many decimal places')
a = p.parse_args()
try:
    with open(a.file, encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        if a.column not in (reader.fieldnames or []):
            p.error(f'unknown column: {a.column}')
        values = [float(row[a.column]) for row in reader]
    print(json.dumps({'column': a.column, 'count': len(values), 'total': sum(values) if a.precision is None else round(sum(values), a.precision)}))
except (OSError, ValueError, TypeError) as error:
    p.error(str(error))
