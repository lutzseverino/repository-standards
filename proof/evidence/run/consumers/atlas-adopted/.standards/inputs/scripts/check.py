"""Atlas's declared, literal-argv contract actions; run in the consumer cwd."""
import json
from pathlib import Path
import sys

LITERAL = 'Atlas input; $(touch SHOULD_NOT_EXIST) & [literal]'
CONTRACT = {'encoding': 'utf-8', 'delimiter': ',', 'header': True}
DOCUMENT = '''# CSV transport contract

Input is UTF-8 text with a comma delimiter and a header row.
See `.csv-summary.json` for the machine-readable transport assumptions.
Numeric conversion and error handling are defined by the summarizer itself.
'''


def execute():
    if len(sys.argv) != 3 or sys.argv[2] != LITERAL:
        raise ValueError('Atlas literal argv was split or interpreted')
    operation = sys.argv[1]
    payload = json.load(sys.stdin)
    selection = payload['selection']
    if not all(key in selection for key in ('identity', 'declarations', 'resolution')):
        raise ValueError('Expected resolved selection identity, declarations, and resolution')
    declaration = payload['declaration']
    expected = {
        'fix-contract': 'data-contract', 'check-contract': 'data-contract',
        'fix-contribution': 'contributing', 'check-contribution': 'contributing',
        'obsolete': 'editor-config',
    }
    if expected.get(operation) != declaration:
        raise ValueError('Wrong declaration supplied to Atlas action')
    with Path('.author-trace.jsonl').open('a') as trace:
        trace.write(json.dumps({'publisher': 'atlas', 'operation': operation,
                                'declaration': declaration, 'argv': sys.argv[1:]}) + '\n')
    if operation == 'obsolete':
        raise ValueError('Obsolete default check ran: complete profile replacement was lost')
    if operation.endswith('contribution'):
        path = Path('CONTRIBUTING.md')
        if operation == 'fix-contribution':
            path.write_text((Path(__file__).parent.parent / 'assets/contributing.md').read_text())
        if 'atlas-public-review' not in path.read_text():
            raise ValueError('Atlas public contribution policy missing (employer must exclude this declaration)')
        return 'Atlas public contribution policy is present'
    path = Path('.csv-summary.json')
    values = json.loads(path.read_text()) if path.exists() else {}
    document = Path('docs/data-contract.md')
    if operation == 'fix-contract':
        values.update(CONTRACT)
        path.write_text(json.dumps(values, indent=2) + '\n')
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(DOCUMENT)
    if not all(values.get(key) == value for key, value in CONTRACT.items()):
        raise ValueError('CSV transport configuration does not match Atlas assumptions')
    if not document.exists() or document.read_text() != DOCUMENT:
        raise ValueError('CSV transport document does not match Atlas assumptions')
    return 'CSV transport config and documentation agree'


try:
    message = execute()
except (ValueError, KeyError, OSError, TypeError) as error:
    print(json.dumps({'status': 'fail', 'message': str(error)}))
    sys.exit(1)
print(json.dumps({'status': 'pass', 'message': message}))
