"""THROWAWAY #80 scenario runner. See README.md for the phased real-agent run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def read(path):
    return json.loads(path.read_text())


def run(root, argv, cwd, expected=0):
    result = subprocess.run([str(a) for a in argv], cwd=cwd, text=True, capture_output=True)
    with (root / 'commands.jsonl').open('a') as stream:
        stream.write(json.dumps({'argv': [str(a) for a in argv], 'cwd': str(cwd), 'exit': result.returncode,
                                 'stdout': result.stdout, 'stderr': result.stderr}) + '\n')
    assert result.returncode == expected, (argv, result.returncode, result.stdout, result.stderr)
    return result.stdout.strip()


def git(root, cwd, *args):
    return run(root, ['git', *args], cwd)


def commit(root, repo, message):
    git(root, repo, 'add', '.')
    git(root, repo, '-c', 'user.name=Prototype Scenario', '-c', 'user.email=proof@example.invalid', 'commit', '-qm', message)
    return git(root, repo, 'rev-parse', 'HEAD')


def snapshot(project):
    result = {}
    for f in sorted(project.rglob('*')):
        if '.git' in f.relative_to(project).parts:
            continue
        if f.is_symlink():
            result[str(f.relative_to(project))] = {'link': str(f.readlink())}
        elif f.is_file():
            result[str(f.relative_to(project))] = {'sha256': hashlib.sha256(f.read_bytes()).hexdigest(),
                                                   'executable': bool(f.stat().st_mode & 0o111)}
    result['@HEAD'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project, text=True).strip()
    result['@index-tree'] = subprocess.check_output(['git', 'write-tree'], cwd=project, text=True).strip()
    return result


def capture(root, project, name):
    result = snapshot(project)
    save(root / 'snapshots' / f'{name}.json', result)
    return result


def cli(root, name, command, *args, expected=0):
    info = read(root / 'run.json')
    return run(root, [sys.executable, info['cli'], command, *args], root / name, expected)


def selection(root, name, revision=None, publisher=None, profile=None):
    info = read(root / 'run.json')
    return ['--source', root / 'publishers' / (publisher or name), '--revision', revision or info['revisions'][name],
            '--profile', profile or {'atlas': 'employer', 'beacon': 'compact'}[name]]


def prepare(root):
    assert not root.exists(), 'choose a new disposable output path'
    root.mkdir(parents=True)
    run(root, [sys.executable, HERE / 'build.py', root / 'depot'], HERE)
    info = {'revisions': {}, 'heads': {}, 'tool_versions': ['0.1.0', '0.2.0'],
            'implementation_base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip()}
    for name in ('atlas', 'beacon'):
        publisher = root / 'publishers' / name
        shutil.copytree(HERE / 'fixtures' / name, publisher)
        git(root, publisher, 'init', '-q')
        info['revisions'][name] = commit(root, publisher, f'Publish {name} independent fixture')
        project = root / name
        shutil.copytree(HERE / 'fixtures/consumers' / name, project)
        git(root, project, 'init', '-q')
        info['heads'][name] = commit(root, project, 'Existing project-owned behavior and content')
        shutil.copytree(project, root / 'before' / name)
        cli_path = run(root, [sys.executable, HERE / 'tool/bootstrap.py', '--depot', root / 'depot',
                              '--version', '0.1.0', '--cache', root / 'installed'], project)
        info['cli'] = cli_path
    save(root / 'run.json', info)
    for name in ('atlas', 'beacon'):
        before = capture(root, root / name, name + '-before-inspect')
        result = json.loads(cli(root, name, 'inspect', *selection(root, name)))
        save(root / f'{name}-inspection.json', result)
        after = capture(root, root / name, name + '-after-inspect')
        assert before == after
        assert '.author-trace.jsonl' not in after
        full = json.loads(cli(root, name, 'inspect', *selection(root, name, profile='full')))
        save(root / f'{name}-full-inspection.json', full)
    atlas, beacon = read(root / 'atlas-inspection.json'), read(root / 'beacon-inspection.json')
    assert atlas['resolution']['contributing'] == 'excluded'
    assert 'checks' not in atlas['declarations']['editor-config']
    assert 'checks' not in beacon['declarations']['operations-record']
    assert atlas['resolution']['csv-work'] == 'inherited'
    assert beacon['resolution']['operations-record'] == 'replaced'
    # Invalid declarations fail through installed public CLI, with consumer unchanged.
    original = root / 'publishers/atlas'
    for case in ('missing-reference', 'conflict', 'reserved-skill', 'missing-prerequisite', 'malformed-result'):
        bad = root / 'publishers' / case
        shutil.copytree(original, bad)
        data = read(bad / 'standards.yaml')
        if case == 'missing-reference':
            data['defaults']['csv-work']['source'] = 'skills/missing'
        elif case == 'conflict':
            data['profiles']['employer']['duplicate'] = data['defaults']['readme']
        elif case == 'reserved-skill':
            data['defaults']['csv-work']['target'] = '.agents/skills/adopt-standards'
        elif case == 'missing-prerequisite':
            data['defaults']['data-contract']['fixes'][0]['requires'].append('proof80-unavailable-runtime')
        else:
            (bad / 'scripts/malformed.py').write_text('print("not a JSON result")\n')
            data['defaults']['data-contract']['checks'][0]['argv'] = ['python3', '{inputs}/scripts/malformed.py']
        save(bad / 'standards.yaml', data)
        rev = commit(root, bad, f'Exercise {case}')
        if case == 'malformed-result':
            info['malformed_revision'] = rev
            save(root / 'run.json', info)
            continue
        before = snapshot(root / 'atlas')
        command = 'apply' if case == 'missing-prerequisite' else 'inspect'
        error = cli(root, 'atlas', command, *selection(root, 'atlas', rev, case), expected=1)
        save(root / f'{case}.json', json.loads(error))
        assert before == snapshot(root / 'atlas')
    save(root / 'assertions-prepare.json', {'read_only_inspection': True, 'inherit_replace_exclude': True,
                                          'actionable_invalid_declarations': True, 'prerequisite_before_mutation': True})


def agent(root, name, stage):
    info = read(root / 'run.json')
    project = root / name
    if stage == 'initial':
        flags = ' '.join(str(a) for a in selection(root, name))
        task = f'Use the shared adoption skill at {root}/bootstrap-SKILL.md and installed CLI {info["cli"]}. Adopt this selected profile: {flags}.'
    elif stage == 'update':
        flags = ' '.join(str(a) for a in selection(root, 'atlas', info['updated_revision']))
        task = f'Use .agents/skills/adopt-standards/SKILL.md to update standards with {flags}.'
    elif stage == 'offline':
        task = 'The publisher is unavailable. Use retained .agents/skills/trace-csv/SKILL.md and rounding.md to investigate a tiny decimal rounding example in the current app. Use project setup and the shared adoption skill to inspect the retained selection and run its checks. Report observed behavior and provenance; no adoption update is requested.'
    else:
        task = 'Use .agents/skills/adopt-standards/SKILL.md to diagnose and recover the incomplete adoption from its retained selection and actual progress. Read the failed script and retained work before retrying.'
    prompt = (f'Work only in this disposable consumer repository: {project}. {task}\n'
              'Use only this consumer, supplied installed tool/bootstrap, and selected publisher inputs. '
              'No planning context or product source checkout is needed. Complete required contextual work from actual project behavior. '
              'Preserve existing project-specific facts and employer-owned contribution policy. Leave adoption changes uncommitted. '
              'Use the shared skill completion contract and report scripted evidence separately from your contextual assessment.\n')
    path = root / 'agents' / f'{name}-{stage}'
    path.parent.mkdir(exist_ok=True)
    path.with_suffix('.prompt.txt').write_text(prompt)
    shutil.copy2(HERE / 'tool/adopt-SKILL.md', root / 'bootstrap-SKILL.md')
    capture(root, project, f'{name}-{stage}-before-agent')
    argv = ['codex', 'exec', '--ignore-user-config', '--ephemeral', '-c', 'approval_policy="never"',
            '--sandbox', 'danger-full-access', '--json', '-C', str(project), '-o', str(path.with_suffix('.final.txt')), '-']
    save(path.with_suffix('.command.json'), {'argv': argv, 'stdin': prompt})
    with path.with_suffix('.jsonl').open('w') as out, path.with_suffix('.stderr.txt').open('w') as err:
        result = subprocess.run(argv, input=prompt, text=True, stdout=out, stderr=err)
    capture(root, project, f'{name}-{stage}-after-agent')
    save(path.with_suffix('.exit.json'), {'exit': result.returncode})
    assert result.returncode == 0, f'agent failed; inspect {path}'
    assert read(project / '.standards/progress.json')['status'] == 'complete', 'agent left adoption incomplete'
    assert snapshot(project)['@HEAD'] == info['heads'][name], 'adoption must not commit'
    print(f'{name} {stage}: actual agent completed; evidence {path}')


def verify_initial(root):
    info = read(root / 'run.json')
    for name in ('atlas', 'beacon'):
        project = root / name
        assert read(project / '.standards/progress.json')['status'] == 'complete'
        assert snapshot(project)['@HEAD'] == info['heads'][name]
        assert (project / 'CONTRIBUTING.md').read_bytes() == (root / 'before' / name / 'CONTRIBUTING.md').read_bytes()
        assert (project / 'README.md').read_bytes() != (root / 'before' / name / 'README.md').read_bytes()
        assert not (project / 'SHOULD_NOT_EXIST').exists()
        trace = (project / '.author-trace.jsonl').read_text()
        assert '"action": "fix-contribution"' not in trace
        events = [json.loads(line) for line in (project / '.standards/events.jsonl').read_text().splitlines()]
        assert not any('contribut' in e.get('operation', '') or 'obsolete' in e.get('operation', '') for e in events)
        shutil.copytree(project, root / 'initial-complete' / name)
    save(root / 'assertions-initial.json', {'uncommitted': True, 'readme_changed_by_real_agent': True,
                                          'excluded_employer_bytes_unchanged': True, 'excluded_operations_absent': True,
                                          'shell_metacharacters_literal': True})


def probes(root):
    info = read(root / 'run.json')
    scratch = root / 'malformed-consumer'
    shutil.copytree(root / 'initial-complete/atlas', scratch)
    cli(root, 'malformed-consumer', 'apply', *selection(root, 'atlas', info['malformed_revision'], 'malformed-result'))
    save(scratch / '.standards/probe-claims.json', read(scratch / '.standards/assessment.json')['claims'])
    error = cli(root, 'malformed-consumer', 'finish', '--assessment', '.standards/probe-claims.json', expected=1)
    save(root / 'malformed-result.json', json.loads(error))
    assert read(scratch / '.standards/progress.json')['status'] == 'incomplete'
    publisher = root / 'publishers/retirement'
    shutil.copytree(root / 'publishers/atlas', publisher)
    data = read(publisher / 'standards.yaml')
    data['profiles']['employer']['csv-work'] = {'exclude': True}
    save(publisher / 'standards.yaml', data)
    revision = commit(root, publisher, 'Retire installed skill explicitly')
    project = root / 'retirement-consumer'
    shutil.copytree(root / 'initial-complete/atlas', project)
    before = capture(root, project, 'retirement-before')
    error = cli(root, 'retirement-consumer', 'apply', *selection(root, 'atlas', revision, 'retirement'), expected=1)
    assert before == capture(root, project, 'retirement-blocked')
    save(root / 'retirement-blocked.json', json.loads(error))
    cli(root, 'retirement-consumer', 'apply', *selection(root, 'atlas', revision, 'retirement'), '--retain-retired', '.agents/skills/trace-csv')
    after = capture(root, project, 'retirement-retained')
    assert all(after[k] == v for k, v in before.items() if k.startswith('.agents/skills/trace-csv/'))
    assert '.agents/skills/trace-csv' not in read(project / '.standards/progress.json')['installed']
    save(root / 'assertions-probes.json', {'malformed_result_incomplete': True, 'retirement_blocked_before_mutation': True,
                                        'explicit_retention_preserves_bytes_and_relinquishes_ownership': True,
                                        'probes_are_incomplete_adoptions': True})


def update_setup(root):
    info = read(root / 'run.json')
    publisher, project = root / 'publishers/atlas', root / 'atlas'
    data = read(publisher / 'standards.yaml')
    old_skill = data['defaults']['csv-work']['source']
    updated = publisher / 'skills/trace-csv-v2'
    updated.mkdir()
    (updated / 'SKILL.md').write_text('---\nname: trace-csv\ndescription: Trace rounding and invalid CSV data during ordinary changes.\n---\n\nRead rounding.md before investigating a rounded total. Ordinary review follows employer CONTRIBUTING.md.\n')
    (updated / 'rounding.md').write_text('Compare unrounded totals with --precision output. Rounding affects display, not input validation.\n')
    data['profiles']['employer']['csv-work'] = {'kind': 'skill', 'mode': 'exact', 'target': '.agents/skills/trace-csv', 'source': 'skills/trace-csv-v2'}
    guidance = publisher / 'guidance/readme-employer.md'
    guidance.write_text(guidance.read_text() + '\nExplain the current rounding option with an observed decimal example, including the default. Preserve current project operational notes.\n')
    save(publisher / 'standards.yaml', data)
    info['updated_revision'] = commit(root, publisher, 'Update complete skill and contextual rounding guidance')
    source = (project / 'app.py').read_text().replace("a = p.parse_args()", "p.add_argument('--precision', type=int, help='round total to this many decimal places')\na = p.parse_args()")
    source = source.replace("'total': sum(values)", "'total': sum(values) if a.precision is None else round(sum(values), a.precision)")
    (project / 'app.py').write_text(source)
    (project / 'README.md').write_text((project / 'README.md').read_text() + '\n## Current operations\n\nThe Wednesday reconciliation now runs at 16:00 Madrid time. Keep input exports local.\n')
    target = project / '.agents/skills/trace-csv/SKILL.md'
    baseline = target.read_bytes()
    target.write_bytes(baseline + b'\nLocal experimental edit: retain until reconciled.\n')
    before = capture(root, project, 'conflict-before')
    error = json.loads(cli(root, 'atlas', 'apply', *selection(root, 'atlas', info['updated_revision']), expected=1))
    after = capture(root, project, 'conflict-after')
    assert before == after
    save(root / 'conflict.json', error)
    target.write_bytes(baseline)
    save(root / 'conflict-reconciliation.json', {'decision': 'Discard the scenario-injected experiment explicitly; restore exact installed bytes and accept publisher v2 skill', 'target': str(target)})
    save(root / 'run.json', info)


def verify_update(root):
    project = root / 'atlas'
    info = read(root / 'run.json')
    state = read(project / '.standards/state.json')
    assert state['identity']['revision'] == info['updated_revision']
    skill = project / '.agents/skills/trace-csv'
    assert {f.name for f in skill.iterdir()} == {'SKILL.md', 'rounding.md'}
    assert '16:00 Madrid' in (project / 'README.md').read_text()
    assert '--precision' in (project / 'README.md').read_text()
    assert state['tool_version'] == '0.1.0'
    assert (project / 'CONTRIBUTING.md').read_bytes() == (root / 'before/atlas/CONTRIBUTING.md').read_bytes()
    shutil.copytree(project, root / 'update-complete/atlas')
    save(root / 'assertions-update.json', {'whole_update_conflict_no_mutation': True, 'complete_skill_replacement': True,
                                         'current_project_notes_preserved': True, 'tool_pin_unchanged': True})


def recovery_setup(root):
    info = read(root / 'run.json')
    publisher = root / 'publishers/atlas'
    data = read(publisher / 'standards.yaml')
    (publisher / 'scripts/recovery.py').write_text('''import json
from pathlib import Path
import sys
context = json.load(sys.stdin)
action = sys.argv[1]
with Path('.recovery-trace.jsonl').open('a') as stream:
    stream.write(json.dumps({'action': action}) + '\\n')
if action == 'first':
    Path('first-fix.txt').write_text('completed once; preserve on retry\\n')
    print(json.dumps({'status':'pass','message':'first fix completed'}))
elif action == 'second':
    Path('partial-work.txt').write_text('actual partial work survives failure\\n')
    marker = Path('.fail-once')
    if marker.exists():
        marker.unlink()
        print(json.dumps({'status':'fail','message':'injected transient failure consumed .fail-once; partial work retained; safe to retry second operation'}))
        sys.exit(1)
    Path('recovered.txt').write_text('second operation finished\\n')
    print(json.dumps({'status':'pass','message':'second operation recovered'}))
else:
    assert Path('recovered.txt').exists()
    print(json.dumps({'status':'pass','message':'recovery artifact exists'}))
''')
    data['profiles']['employer']['zz-recovery'] = {'kind': 'concern', 'mode': 'contextual',
        'guidance': ['guidance/recovery.md'],
        'fixes': [{'id': action, 'argv': ['python3', '{inputs}/scripts/recovery.py', action], 'requires': ['python3']} for action in ['first', 'second']],
        'checks': [{'id': 'recovery-check', 'argv': ['python3', '{inputs}/scripts/recovery.py', 'check'], 'requires': ['python3']}]}
    (publisher / 'guidance/recovery.md').write_text('Verify that the transient-failure exercise preserves first-fix.txt and partial-work.txt and produces recovered.txt on retry. These are proof records, not product features.\n')
    save(publisher / 'standards.yaml', data)
    info['recovery_revision'] = commit(root, publisher, 'Exercise failure after changes begin')
    project = root / 'recovery'
    shutil.copytree(root / 'atlas', project)
    info['heads']['recovery'] = info['heads']['atlas']
    (project / '.fail-once').write_text('scenario-owned transient fault\n')
    save(root / 'run.json', info)
    capture(root, project, 'recovery-before-failure')
    error = cli(root, 'recovery', 'apply', *selection(root, 'atlas', info['recovery_revision']), expected=1)
    capture(root, project, 'recovery-after-failure')
    save(root / 'injected-failure.json', json.loads(error))
    assert (project / 'first-fix.txt').exists() and (project / 'partial-work.txt').exists()
    assert read(project / '.standards/progress.json')['status'] == 'incomplete'
    bypass = cli(root, 'recovery', 'finish', '--assessment', '.standards/agent-claims.json', expected=1)
    assert 'required fixes are incomplete' in bypass
    save(root / 'incomplete-fix-gate.json', json.loads(bypass))


def verify_recovery(root):
    project = root / 'recovery'
    actions = [json.loads(line)['action'] for line in (project / '.recovery-trace.jsonl').read_text().splitlines()]
    assert actions.count('first') == 1 and actions.count('second') == 2
    assert read(project / '.standards/progress.json')['status'] == 'complete'
    assert (project / 'partial-work.txt').read_text() == 'actual partial work survives failure\n'
    assert (project / 'CONTRIBUTING.md').read_bytes() == (root / 'before/atlas/CONTRIBUTING.md').read_bytes()
    assert snapshot(project)['@HEAD'] == read(root / 'run.json')['heads']['recovery']
    save(root / 'assertions-recovery.json', {'employer_bytes_and_head_unchanged': True, 'actual_partial_work_retained': True, 'completed_fix_ran_once': True,
                                          'failed_fix_retried': True, 'real_agent_completed_recovery': True})


def offline(root):
    info = read(root / 'run.json')
    project = root / 'atlas'
    # Explicit scenario commit AFTER assertions established adoption did not commit.
    if not (root / 'fresh').exists():
        info['consumer_commit'] = commit(root, project, 'Scenario only: retain verified adoption inputs')
        save(root / 'run.json', info)
        git(root, root, 'clone', '-q', project, root / 'fresh')
    else:
        info['consumer_commit'] = git(root, root / 'fresh', 'rev-parse', 'HEAD')
        assert git(root, project, 'rev-parse', 'HEAD') == info['consumer_commit']
    if (root / 'publishers').exists():
        (root / 'publisher-history').mkdir(exist_ok=True)
        for publisher in sorted((root / 'publishers').iterdir()):
            git(root, publisher, 'bundle', 'create', root / 'publisher-history' / f'{publisher.name}.bundle', '--all')
        shutil.rmtree(root / 'publishers')
    assert not (root / 'publishers').exists()
    fresh = root / 'fresh'
    pin_before = read(fresh / '.standards/tool.json')
    installed = run(root, [sys.executable, '.standards/setup.py', '--cache', root / 'fresh-install'], fresh)
    assert Path(installed).is_file() and not Path(installed).is_relative_to(fresh)
    info['offline_cli'] = installed
    # General installation deliberately changes, leaving project pin untouched.
    shutil.copy2(root / 'depot/standards-0.2.0.pyz', root / 'general-standards.pyz')
    assert json.loads(run(root, [sys.executable, root / 'general-standards.pyz', 'version'], fresh))['version'] == '0.2.0'
    assert read(fresh / '.standards/tool.json') == pin_before
    run(root, [sys.executable, root / 'general-standards.pyz', 'inspect'], fresh, expected=1)
    before = capture(root, fresh, 'offline-before-inspect')
    inspected = json.loads(run(root, [sys.executable, installed, 'inspect'], fresh))
    assert before == capture(root, fresh, 'offline-after-inspect')
    run(root, [sys.executable, installed, 'check'], fresh)
    assert read(fresh / '.standards/tool.json') == pin_before
    # Retained ordinary-work resource and guidance are genuinely readable.
    assert (fresh / '.agents/skills/trace-csv/rounding.md').read_text()
    assert inspected['material']['guidance/readme-employer.md']['text']
    info['heads']['fresh'] = info['consumer_commit']
    save(root / 'run.json', info)
    agent(root, 'fresh', 'offline')
    selection_before = read(fresh / '.standards/selection.json')
    new_cli = run(root, [sys.executable, '.standards/setup.py', '--depot', root / 'depot', '--version', '0.2.0', '--cache', root / 'fresh-install'], fresh)
    assert read(fresh / '.standards/selection.json') == selection_before
    run(root, [sys.executable, new_cli, 'check'], fresh)
    assert read(fresh / '.standards/tool.json')['version'] == '0.2.0'
    # Artifact integrity is verified on setup, without publisher access.
    corrupt = root / 'corrupt-cache' / pin_before['sha256'] / Path(installed).name
    corrupt.parent.mkdir(parents=True)
    corrupt.write_text('corrupted installation')
    scratch = root / 'integrity'
    shutil.copytree(root / 'initial-complete/atlas', scratch)
    run(root, [sys.executable, '.standards/setup.py', '--cache', root / 'corrupt-cache'], scratch, expected=1)
    save(root / 'run.json', info)
    save(root / 'assertions-offline.json', {'scenario_commit_after_uncommitted_verification': True, 'publisher_unavailable': True,
                                         'fresh_checkout_retained_inputs_and_checks': True, 'cli_installed_outside_consumer': True,
                                         'routine_versions_stable': True, 'general_install_does_not_override_pin': True,
                                         'deliberate_tool_update_preserves_standards': True, 'corrupt_install_rejected': True})


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('phase', choices=['prepare', 'agent', 'verify-initial', 'probes', 'update-setup', 'verify-update', 'recovery-setup', 'verify-recovery', 'offline'])
p.add_argument('root', type=Path)
p.add_argument('--consumer', choices=['atlas', 'beacon', 'recovery', 'fresh'])
p.add_argument('--stage', choices=['initial', 'update', 'recovery', 'offline'])
a = p.parse_args()
if a.phase == 'agent':
    agent(a.root.resolve(), a.consumer, a.stage)
else:
    globals()[a.phase.replace('-', '_')](a.root.resolve())
