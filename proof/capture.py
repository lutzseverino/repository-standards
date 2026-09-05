"""Retain inspectable evidence from a completed disposable scenario directory."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

root = Path(sys.argv[1]).resolve()
out = Path(__file__).resolve().parent / 'evidence/run'
assert not out.exists(), 'capture once into an absent evidence destination'
for phase in ('prepare', 'initial', 'probes', 'update', 'recovery', 'offline'):
    assert (root / f'assertions-{phase}.json').is_file(), phase
out.mkdir()
for file in sorted(root.iterdir()):
    if file.is_file():
        shutil.copy2(file, out / file.name)
for name in ('agents', 'snapshots', 'depot', 'publisher-history'):
    shutil.copytree(root / name, out / name)
for label, source in {
    'atlas-before': 'before/atlas', 'beacon-before': 'before/beacon',
    'atlas-adopted': 'initial-complete/atlas', 'beacon-adopted': 'initial-complete/beacon',
    'atlas-updated': 'update-complete/atlas', 'recovery': 'recovery', 'fresh': 'fresh',
    'malformed-incomplete': 'malformed-consumer', 'retirement-incomplete': 'retirement-consumer',
}.items():
    shutil.copytree(root / source, out / 'consumers' / label,
                    ignore=shutil.ignore_patterns('.git', '__pycache__'))
(out / 'consumer-history').mkdir()
subprocess.run(['git', '-C', str(root / 'atlas'), 'bundle', 'create',
                str(out / 'consumer-history/atlas.bundle'), '--all'], check=True)
info = json.loads((root / 'run.json').read_text())
with zipfile.ZipFile(info['cli']) as installed:
    for name in ('__main__.py', 'bootstrap.py', 'adopt-SKILL.md'):
        assert installed.read(name) == (Path(__file__).parent / 'tool' / name).read_bytes()
identity = {'python': sys.version, 'platform': platform.platform(),
            'git': subprocess.check_output(['git', '--version'], text=True).strip(),
            'codex': subprocess.check_output(['codex', '--version'], text=True).strip(),
            'executed_cli_matches_tool_source': True,
            'source_base_at_capture': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}
(out / 'environment.json').write_text(json.dumps(identity, indent=2) + '\n')
files = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(out.rglob('*')) if p.is_file()}
(out / 'SHA256SUMS.json').write_text(json.dumps(files, indent=2) + '\n')
print(f'Retained {len(files)} evidence files in {out}')
