#!/usr/bin/env python3
"""Sync sanitized v5 metadata and regenerate the user's consolidated result file."""
from pathlib import Path
import argparse,json,subprocess,sys

REMOTE_ROOT = '/home/sy23985/Storage/acl2027_server_v5_20260914'
APPWORLD_ROOT = '/home/sy23985/Storage/acl2027_appworld_ace_20260915'
SSH = ['ssh', '-S', '/Users/tom/.ssh/acl2027-miata-control', '-o', 'BatchMode=yes',
       '-o', 'ConnectTimeout=10', 'sy23985@miata.ischool.utexas.edu']


def sync_appworld(project):
    """Mirror AppWorld scheduler state, official reports, task progress and trained playbooks.

    A failure here leaves the previous AppWorld mirror in place and never blocks the v5 refresh.
    """
    script = '''from pathlib import Path
import json
root=Path(%r);out={'files':{},'progress':{},'playbooks':{}}
for name in ['orchestrator/state.json','jobs.json','smoke/report.json','SOURCE_COMMIT','config_audit.json']:
    p=root/name
    if p.is_file():out['files'][name]=p.read_text()
for p in sorted((root/'evaluations').glob('*.txt')):out['files']['evaluations/'+p.name]=p.read_text()
jobs=json.loads((root/'jobs.json').read_text()) if (root/'jobs.json').is_file() else {}
for name in jobs:
    tasks=root/'source/experiments/outputs'/name/'tasks'; events=root/'calls'/name/'events.jsonl'
    kinds=[json.loads(x)['kind'] for x in events.read_text().splitlines() if x.strip()] if events.is_file() else []
    out['progress'][name]=dict(tasks=len([t for t in tasks.iterdir() if t.is_dir()]) if tasks.is_dir() else 0,
        context_exhausted=kinds.count('context_exhausted'),output_ceiling=kinds.count('output_ceiling'),
        incomplete_response=kinds.count('incomplete_response'))
for p in sorted((root/'playbooks').rglob('*.txt')):out['playbooks'][str(p.relative_to(root/'playbooks'))]=p.read_text()
print(json.dumps(out))
''' % APPWORLD_ROOT
    response = subprocess.run(SSH+['python3 -'], input=script, text=True, capture_output=True, timeout=60)
    if response.returncode: return None
    content = json.loads(response.stdout)
    mirror, playbooks = project/'Storage/server_v5_preparation/appworld', project/'Storage/appworld_ace_qwen/playbooks'
    for base, files in [(mirror, content['files']), (playbooks, content['playbooks'])]:
        for name, text in files.items():
            destination = base/name; destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.with_suffix(destination.suffix+'.tmp'); temp.write_text(text); temp.replace(destination)
    (mirror/'progress.json').write_text(json.dumps(content['progress'], indent=2)+'\n')
    return len(content['files']) + len(content['playbooks'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--no-upload', action='store_true')
    args = parser.parse_args()
    prep = args.project/'Storage/server_v5_preparation'
    script = '''from pathlib import Path
import json
root=Path(%r)
paths=[]
paths.extend(sorted(root.glob('derived/*/results.json')))
for stage in sorted((root/'evaluation').glob('*')):
    if not stage.is_dir():continue
    for name in ['manifest.json','results.json','queue.json','pipeline_status.json','tests.json','preflight/report.json']:
        paths.append(stage/name)
for name in ['ACTIVE_ADAPTATION_STAGE.json','ACTIVE_OPTIMIZATION_STAGE.json','ACTIVE_JUDGE_STAGE.json','prediction_manifest.json','prediction_queue.json','results.json','RESULTS.md','METRICS.md']:
    paths.append(root/name)
for stage in sorted((root/'stages').glob('*')):
    if not stage.is_dir():continue
    for name in ['manifest.json','plan.json','results.json','RESULTS.md','METRICS.md','queue.json','tests.json','dispatch.json','pipeline_status.json','preflight/report.json','SUPERSEDED_BY.json','DC_SUPERSEDED_BY.json']:
        paths.append(stage/name)
for name in ['dispatch.json','queue.json','MANIFEST.json','ACE_PREFIX_AUDIT.json']:
    paths.append(root/'joint_adaptation'/name)
for recovery in sorted(root.glob('recovery_dc_*')):
    if recovery.is_dir():
        for name in ['dispatch.json','queue.json','MANIFEST.json','VALIDATION.json','DIAGNOSIS.json']:
            paths.append(recovery/name)
        paths.extend(recovery.glob('*/PREFIX_AUDIT.json'))
print(json.dumps({str(p.relative_to(root)):p.read_text() for p in paths if p.is_file()}))
''' % REMOTE_ROOT
    response = subprocess.run(SSH+['python3 -'], input=script, text=True, capture_output=True, timeout=35)
    if response.returncode:
        raise RuntimeError('SSH metadata sync failed; existing snapshots remain unchanged')
    content = json.loads(response.stdout)
    for name,text in content.items():
        if name.startswith('stages/'):
            rel=Path(name).relative_to('stages')
        elif name in ('ACTIVE_ADAPTATION_STAGE.json','ACTIVE_OPTIMIZATION_STAGE.json','ACTIVE_JUDGE_STAGE.json') or name.startswith(('joint_adaptation/', 'recovery_dc_', 'evaluation/', 'derived/')):rel=Path(name)
        else:rel=Path('live')/name
        destination=prep/rel;destination.parent.mkdir(parents=True,exist_ok=True)
        temp=destination.with_suffix(destination.suffix+'.tmp');temp.write_text(text);temp.replace(destination)
    try: appworld = sync_appworld(args.project)
    except (subprocess.SubprocessError, ValueError, OSError): appworld = None
    output=args.project/'Storage/v5_results.md'
    subprocess.run([sys.executable,str(Path(__file__).with_name('export_results.py')),
        '--prep',str(prep),'--protocol',str(args.project/'Storage/experiment_guidelines/four_corpus_server_v5/protocol.json'),
        '--output',str(output)],check=True)
    subprocess.run([sys.executable,str(Path(__file__).with_name('export_html.py')),str(output)],check=True,capture_output=True)
    if not args.no_upload:
        subprocess.run(['scp','-o','ControlPath=/Users/tom/.ssh/acl2027-miata-control','-o','BatchMode=yes',
            str(output),str(output.with_suffix('.snapshot.json')),
            'sy23985@miata.ischool.utexas.edu:'+REMOTE_ROOT+'/'],check=True,timeout=35)
    print(json.dumps({'metadata_files_synced':len(content),'appworld_files_synced':appworld,'uploaded':not args.no_upload}))


if __name__=='__main__':main()
