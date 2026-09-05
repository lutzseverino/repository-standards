"""Thin prototype bootstrap: acquire/verify an installed project-pinned zipapp."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--depot', type=Path)
p.add_argument('--version')
p.add_argument('--cache', type=Path, default=Path.home() / '.cache/standards-proof80')
a = p.parse_args()
pin_path = Path('.standards/tool.json')
if a.version:
    artifact = (a.depot / f'standards-{a.version}.pyz').resolve()
    catalogue = json.loads((a.depot / 'catalogue.json').read_text())
    pin = {'version': a.version, 'sha256': catalogue[a.version], 'artifact': str(artifact)}
else:
    pin = json.loads(pin_path.read_text())
artifact = Path(pin['artifact'])
installed = a.cache / pin['sha256'] / artifact.name
if not installed.exists():
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == pin['sha256'], 'artifact digest mismatch'
    installed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact, installed)
assert hashlib.sha256(installed.read_bytes()).hexdigest() == pin['sha256'], 'installed digest mismatch'
if a.version:
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_text(json.dumps(pin, indent=2) + '\n')
print(installed)
