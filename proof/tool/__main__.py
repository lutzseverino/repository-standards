"""THROWAWAY proof #80: installed, publisher-neutral adoption support."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

VERSION = json.loads(zipfile.ZipFile(sys.argv[0]).read('version.json'))['version']
RESERVED = {'adopt-standards', 'setup-standards'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def safe(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p) != name:
        raise ValueError(f'unsafe relative path {name!r}; use a normalized relative path')
    return name


def inventory(path):
    if path.is_symlink():
        raise ValueError(f'symlink unsupported: {path}')
    if not path.exists():
        return {}
    files = [path] if path.is_file() else sorted(path.rglob('*'))
    result = {}
    for f in files:
        if f.is_symlink():
            raise ValueError(f'symlink unsupported: {f}')
        if f.is_file():
            result['.' if f == path else f.relative_to(path).as_posix()] = {
                'sha256': digest(f.read_bytes()), 'executable': bool(f.stat().st_mode & 0o111)}
    return result


def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f'duplicate declaration/key {k!r}; give each identity one owner')
        result[k] = v
    return result


def prerequisite(req):
    if isinstance(req, str):
        return {'requirement': req, 'available': shutil.which(req) is not None}
    raise ValueError('requires entries must be executable names; preinstall dependencies explicitly')


def resolve(inputs, identity):
    raw = json.loads((inputs / 'standards.yaml').read_text(), object_pairs_hook=unique)
    if set(raw) != {'publisher', 'defaults', 'profiles'}:
        raise ValueError('standards.yaml requires publisher, defaults, profiles only')
    if identity['profile'] not in raw['profiles']:
        raise ValueError(f"unknown profile {identity['profile']!r}; choose {list(raw['profiles'])}")
    defaults, overrides = raw['defaults'], raw['profiles'][identity['profile']]
    effective, resolution = {}, {}
    for key in sorted(defaults.keys() | overrides.keys()):
        item = overrides.get(key, defaults.get(key))
        if item == {'exclude': True}:
            if key not in defaults:
                raise ValueError(f'{key}: cannot exclude an unknown default')
            resolution[key] = 'excluded'
            continue
        resolution[key] = ('replaced' if key in defaults else 'added') if key in overrides else 'inherited'
        effective[key] = item
    targets = []
    material = {}
    for key, d in effective.items():
        if not isinstance(d, dict) or set(d) - {'kind', 'mode', 'target', 'source', 'guidance', 'fixes', 'checks'}:
            raise ValueError(f'{key}: unsupported declaration fields; replacement must be complete')
        if d.get('kind') not in {'file', 'skill', 'concern'} or d.get('mode') not in {'exact', 'contextual'}:
            raise ValueError(f'{key}: declare kind file/skill/concern and mode exact/contextual')
        if d['kind'] == 'concern' and ('target' in d or d['mode'] != 'contextual'):
            raise ValueError(f'{key}: repository concern is contextual and has no fake target')
        if d['kind'] != 'concern':
            target = safe(d['target'])
            if target.split('/')[0] in {'.git', '.standards'}:
                raise ValueError(f'{key}: {target} is reserved system state')
            if target == '.agents' or target.startswith('.agents/'):
                parts = target.split('/')
                if d['kind'] != 'skill' or len(parts) != 3 or parts[:2] != ['.agents', 'skills'] or parts[2] in RESERVED:
                    raise ValueError(f'{key}: reserved system skills cannot be replaced; use an ordinary-work skill name')
            for other in targets:
                if target == other or target.startswith(other + '/') or other.startswith(target + '/'):
                    raise ValueError(f'{key}: conflicting target {target} overlaps {other}; keep one complete owner')
            targets.append(target)
        refs = list(d.get('guidance', []))
        if d['mode'] == 'exact':
            refs.append(d['source'])
            src = inputs / safe(d['source'])
            if d['kind'] == 'skill':
                text = (src / 'SKILL.md').read_text() if (src / 'SKILL.md').exists() else ''
                if not text.startswith('---\n') or not re.search(r'\nname: .+', text) or not re.search(r'\ndescription: .+', text):
                    raise ValueError(f'{key}: skill needs Agent Skills SKILL.md frontmatter')
            elif not src.is_file():
                raise ValueError(f'{key}: exact file source {src} is not a file')
        for phase in ('fixes', 'checks'):
            ids = set()
            for op in d.get(phase, []):
                if set(op) != {'id', 'argv', 'requires'} or op['id'] in ids:
                    raise ValueError(f'{key}/{phase}: declare unique id, argv, requires')
                ids.add(op['id'])
                if not op['argv'] or not all(isinstance(a, str) for a in op['argv']):
                    raise ValueError(f'{key}/{op["id"]}: argv must be a nonempty literal string array')
                if op['argv'][0] not in op['requires']:
                    raise ValueError(f'{key}/{op["id"]}: declare executable {op["argv"][0]} in requires')
                for arg in op['argv']:
                    if arg.startswith('{inputs}/'):
                        refs.append(arg.removeprefix('{inputs}/'))
                for req in op['requires']:
                    prerequisite(req)
        for ref in refs:
            src = inputs / safe(ref)
            if not src.exists():
                raise ValueError(f'{key}: missing reference {ref}; add it to the publisher commit or correct the path')
            inventory(src)
            for f in ([src] if src.is_file() else sorted(src.rglob('*'))):
                if f.is_file():
                    material[f.relative_to(inputs).as_posix()] = {'sha256': digest(f.read_bytes()), 'text': f.read_text()}
    return {'identity': {**identity, 'publisher': raw['publisher']}, 'declarations': effective,
            'resolution': resolution, 'material': material,
            'prerequisites': {f'{key}/{phase}/{op["id"]}': [prerequisite(r) for r in op['requires']]
                              for key, d in effective.items() for phase in ('fixes', 'checks') for op in d.get(phase, [])}}


def acquire(source, revision, destination):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('revision must be an immutable full 40-character Git commit')
    data = subprocess.run(['git', '-C', source, 'archive', revision], check=True, capture_output=True).stdout
    archive = destination.parent / 'source.tar'
    archive.write_bytes(data)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            safe(member.name.rstrip('/'))
            if not (member.isfile() or member.isdir()):
                raise ValueError(f'publisher archive contains unsupported link/device {member.name}')
        tar.extractall(destination, filter='data')


def system_files():
    with zipfile.ZipFile(sys.argv[0]) as z:
        return {'.agents/skills/adopt-standards/SKILL.md': z.read('adopt-SKILL.md'),
                '.standards/setup.py': z.read('bootstrap.py')}


def proposed(inputs, selection):
    outputs = {}
    for d in selection['declarations'].values():
        if d['mode'] == 'exact':
            outputs[d['target']] = inventory(inputs / d['source'])
    for target, data in system_files().items():
        outputs[target] = {'.': {'sha256': digest(data), 'executable': False}}
    return outputs


def conflicts(project, old, desired, retained):
    problems = []
    for target, baseline in old.items():
        if inventory(project / target) != baseline:
            problems.append(f'{target}: local installed-content edit; reconcile against .standards/state.json baseline')
        if target not in desired and target not in retained:
            problems.append(f'{target}: retired installed content; explicitly --retain-retired {target} to preserve and relinquish ownership')
    for target, content in desired.items():
        if target not in old and (project / target).exists() and inventory(project / target) != content:
            problems.append(f'{target}: preexisting content differs; reconcile before installing exact content')
    return problems


def record(project, event):
    p = project / '.standards/events.jsonl'
    with p.open('a') as stream:
        stream.write(json.dumps(event) + '\n')


def execute(project, selection, phase, journal, resume=True):
    for key, d in selection['declarations'].items():
        for op in d.get(phase, []):
            ident = f'{key}/{phase}/{op["id"]}'
            if resume and ident in journal['completed']:
                record(project, {'operation': ident, 'status': 'skipped-completed'})
                continue
            missing = [r for r in op['requires'] if not prerequisite(r)['available']]
            if missing:
                record(project, {'operation': ident, 'status': 'prerequisite-missing', 'missing': missing})
                raise ValueError(f'{ident}: missing prerequisites {missing}; install explicitly then retry; operation was not started')
            argv = [a.replace('{inputs}', str(project / '.standards/inputs')) for a in op['argv']]
            payload = {'selection': selection, 'declaration': key}
            run = subprocess.run(argv, cwd=project, input=json.dumps(payload), text=True, capture_output=True)
            evidence = {'operation': ident, 'argv': argv, 'input': payload, 'returncode': run.returncode,
                        'stdout': run.stdout, 'stderr': run.stderr}
            record(project, evidence)
            try:
                result = json.loads(run.stdout)
                valid = isinstance(result, dict) and result.get('status') in {'pass', 'fail'} and isinstance(result.get('message'), str)
            except ValueError:
                valid = False
            if not valid or run.returncode or result['status'] != 'pass':
                raise ValueError(f'{ident}: failed; inspect .standards/events.jsonl, diagnose retained changes, then retry')
            if ident not in journal['completed']:
                journal['completed'].append(ident)
            write(project / '.standards/progress.json', journal)


def apply(project, inputs, selection, retained):
    state_path = project / '.standards/state.json'
    progress_path = project / '.standards/progress.json'
    state = read(state_path) if state_path.exists() else {'baseline': {}}
    journal = read(progress_path) if progress_path.exists() else None
    fingerprint = digest(json.dumps(selection, sort_keys=True).encode())
    desired = proposed(inputs, selection)
    resuming = journal and journal['fingerprint'] == fingerprint and journal['status'] == 'incomplete'
    if resuming:
        # Exact installation already completed; edits still cannot be silently overwritten.
        problems = conflicts(project, journal['installed'], desired, retained)
    else:
        if journal and journal['status'] == 'incomplete':
            raise ValueError('another adoption is incomplete; resume its retained selection before changing pins')
        problems = conflicts(project, state['baseline'], desired, retained)
    if problems:
        raise ValueError('whole update blocked before mutation:\n' + '\n'.join(problems))
    missing = {k: [r['requirement'] for r in v if not r['available']] for k, v in selection['prerequisites'].items()}
    missing = {k: v for k, v in missing.items() if v}
    if missing:
        raise ValueError(f'missing prerequisites before application: {missing}; install explicitly and retry')
    if not resuming:
        dest = project / '.standards/inputs'
        if inputs.resolve() != dest.resolve():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(inputs, dest)
        write(project / '.standards/selection.json', selection)
        for d in selection['declarations'].values():
            if d['mode'] != 'exact':
                continue
            target, src = project / d['target'], dest / d['source']
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_dir():
                shutil.rmtree(target)
            if src.is_dir():
                shutil.copytree(src, target)
            else:
                shutil.copy2(src, target)
        for target, data in system_files().items():
            p = project / target
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        journal = {'fingerprint': fingerprint, 'status': 'incomplete', 'completed': [],
                   'installed': desired, 'retained_retired': retained, 'stage': 'exact-installed'}
        write(progress_path, journal)
        record(project, {'stage': 'exact-installed', 'identity': selection['identity']})
    execute(project, selection, 'fixes', journal)
    journal['stage'] = 'contextual-work-required'
    write(progress_path, journal)
    return {'status': 'incomplete', 'stage': journal['stage'], 'contextual': {
        k: d for k, d in selection['declarations'].items() if d['mode'] == 'contextual'}}


def finish(project, selection, assessment_path):
    journal = read(project / '.standards/progress.json')
    if journal['fingerprint'] != digest(json.dumps(selection, sort_keys=True).encode()):
        raise ValueError('selection differs from active progress; resume the selected adoption')
    required_fixes = {f'{key}/fixes/{op["id"]}' for key, d in selection['declarations'].items() for op in d.get('fixes', [])}
    if not required_fixes.issubset(journal['completed']):
        raise ValueError('required fixes are incomplete; diagnose and resume apply before finish')
    assessment = read(Path(assessment_path))
    required = {k for k, d in selection['declarations'].items() if d['mode'] == 'contextual'}
    if set(assessment) != required or any(not isinstance(v, str) or len(v.strip()) < 30 for v in assessment.values()):
        raise ValueError(f'contextual assessment must explain factual evidence for exactly {sorted(required)}')
    for target, baseline in journal['installed'].items():
        if inventory(project / target) != baseline:
            raise ValueError(f'{target}: installed content changed after application; reconcile before finish')
    # Persist incomplete before checks so a later failed verification cannot leave success status.
    journal['status'] = 'incomplete'
    write(project / '.standards/progress.json', journal)
    execute(project, selection, 'checks', journal, resume=False)
    write(project / '.standards/assessment.json', {'kind': 'agent-assessment', 'claims': assessment})
    write(project / '.standards/state.json', {'identity': selection['identity'], 'tool_version': VERSION,
                                             'baseline': journal['installed'], 'retained_retired': journal['retained_retired']})
    journal.update(status='complete', stage='checks-and-contextual-assessment-complete')
    write(project / '.standards/progress.json', journal)
    return {'status': 'complete', 'scripted_evidence': '.standards/events.jsonl',
            'contextual_assessment': '.standards/assessment.json', 'commit': 'left to selected ordinary workflow'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['version', 'inspect', 'apply', 'finish', 'check'])
    parser.add_argument('--source')
    parser.add_argument('--revision')
    parser.add_argument('--profile')
    parser.add_argument('--assessment')
    parser.add_argument('--retain-retired', action='append', default=[])
    args = parser.parse_args()
    if args.command == 'version':
        return {'version': VERSION}
    project = Path.cwd()
    pin = read(project / '.standards/tool.json')
    if pin['version'] != VERSION or pin['sha256'] != digest(Path(sys.argv[0]).read_bytes()):
        raise ValueError('installed CLI does not match project tool pin; run .standards/setup.py')
    with tempfile.TemporaryDirectory(prefix='standards-inputs-') as tmp:
        if args.source:
            if not args.revision or not args.profile:
                raise ValueError('source selection requires revision and one profile')
            inputs = Path(tmp) / 'inputs'
            acquire(args.source, args.revision, inputs)
            selection = resolve(inputs, {'source': str(Path(args.source).resolve()), 'revision': args.revision, 'profile': args.profile})
        else:
            inputs = project / '.standards/inputs'
            previous = read(project / '.standards/selection.json')
            selection = resolve(inputs, previous['identity'])
            if {k: v for k, v in selection.items() if k != 'prerequisites'} != {k: v for k, v in previous.items() if k != 'prerequisites'}:
                raise ValueError('retained inputs differ from pinned selection; reconcile deliberately')
        if args.command == 'inspect':
            return selection
        if args.command == 'apply':
            return apply(project, inputs, selection, args.retain_retired)
        if args.command == 'finish':
            return finish(project, selection, args.assessment)
        journal = read(project / '.standards/progress.json')
        execute(project, selection, 'checks', journal, resume=False)
        return {'status': 'checks-passed', 'contextual': 'not reassessed by check'}


try:
    print(json.dumps(main(), indent=2))
except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
    print(json.dumps({'status': 'incomplete', 'error': str(error)}, indent=2))
    sys.exit(1)
