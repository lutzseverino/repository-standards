"""Build immutable local prototype artifacts; no publication claim."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

source = Path(__file__).parent / 'tool'
depot = Path(sys.argv[1])
depot.mkdir(parents=True, exist_ok=True)
checksums = {}
for version in ['0.1.0', '0.2.0']:
    artifact = depot / f'standards-{version}.pyz'
    with zipfile.ZipFile(artifact, 'w') as z:
        for f in sorted(source.iterdir()):
            if f.is_file():
                info = zipfile.ZipInfo(f.name, (2026, 9, 5, 0, 0, 0))
                z.writestr(info, f.read_bytes())
        z.writestr(zipfile.ZipInfo('version.json', (2026, 9, 5, 0, 0, 0)), json.dumps({'version': version}))
    checksums[version] = hashlib.sha256(artifact.read_bytes()).hexdigest()
(depot / 'catalogue.json').write_text(json.dumps(checksums, indent=2) + '\n')
print(json.dumps(checksums, indent=2))
