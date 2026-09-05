import json
from pathlib import Path
import sys
context = json.load(sys.stdin)
action = sys.argv[1]
with Path('.recovery-trace.jsonl').open('a') as stream:
    stream.write(json.dumps({'action': action}) + '\n')
if action == 'first':
    Path('first-fix.txt').write_text('completed once; preserve on retry\n')
    print(json.dumps({'status':'pass','message':'first fix completed'}))
elif action == 'second':
    Path('partial-work.txt').write_text('actual partial work survives failure\n')
    marker = Path('.fail-once')
    if marker.exists():
        marker.unlink()
        print(json.dumps({'status':'fail','message':'injected transient failure consumed .fail-once; partial work retained; safe to retry second operation'}))
        sys.exit(1)
    Path('recovered.txt').write_text('second operation finished\n')
    print(json.dumps({'status':'pass','message':'second operation recovered'}))
else:
    assert Path('recovered.txt').exists()
    print(json.dumps({'status':'pass','message':'recovery artifact exists'}))
