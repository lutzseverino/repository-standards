"""Inventory inline Markdown links from one UTF-8 file; offline regex extraction."""
import argparse
import json
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('file', help='Markdown input file')
a = p.parse_args()
try:
    markdown = Path(a.file).read_text(encoding='utf-8')
except OSError as error:
    p.error(str(error))
# Deliberately small parser: nested brackets/parentheses and reference links unsupported.
links = [{'text': text, 'url': url} for text, url in re.findall(r'\[([^\[\]]*)\]\(([^()]*)\)', markdown)]
print(json.dumps(links))
