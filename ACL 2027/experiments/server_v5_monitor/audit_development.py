"""Read-only checkpoint audit; reports only counts and hashes, never corpus content."""
from pathlib import Path
import argparse,hashlib,json,sys,time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=Path,required=True)
    args=parser.parse_args();stage=args.stage
    plan=json.loads((stage/'plan.json').read_text());parent=Path(plan['parent'])
    sys.path[:0]=[str(stage/'code'),str(parent/'code')]
    from core import load,digest,validate_output,rows
    from adapters import EMPTY
    case_count=prediction_count=update_count=reference_count=0
    for cell in [c for c in plan['cells'] if c['seed']==42]:
        d=stage/'preflight'/cell['id'];state=load(d/'state.json')
        assert state['status']=='prediction_complete' and state['predicted']==6 and state['updated']==6
        task=load(parent/'tasks.json')[cell['dataset']]
        sources={r['record_id']:r for r in rows(parent/'data'/cell['dataset']/'dev.jsonl')}
        memory=EMPTY if cell['method']=='ace' else '(empty)'
        phases=['adaptation','evaluation'] if cell['phase']=='offline' else ['evaluation']
        for phase in phases:
            updating=phase=='adaptation' or cell['phase']=='online'
            for i in range(6):
                pred=load(d/(('adaptation_prediction_' if phase=='adaptation' else 'prediction_')+f'{i:03d}.json'))
                source=sources[pred['record_id']]
                assert pred['valid'] and pred['index']==i and pred['memory_before_sha256']==digest(memory)
                assert pred['source_sha256']==hashlib.sha256(source['text'].encode()).hexdigest()
                assert pred['output_sha256']==digest(pred['output'])
                validate_output(pred['output'],task['labels'],task['single_label'])
                prediction_count+=1
                if updating:
                    update=load(d/'updates'/f'{phase}_{i:03d}.json')
                    assert update['record_id']==pred['record_id'] and update['index']==i
                    assert update['prediction_sha256']==pred['output_sha256']
                    assert update['memory_before_sha256']==digest(memory)
                    assert update['memory_after_sha256']==digest(update['memory'])
                    assert pred['committed_at']<=update['completed_at']
                    memory=update['memory'];update_count+=1
                    receipt=d/'feedback_receipts'/f'{phase}_{i:03d}.json'
                    if cell['adaptation_gt']=='yes':
                        feedback=load(receipt)
                        assert feedback['prediction_sha256']==pred['output_sha256']
                        assert feedback['reference_sha256']==digest(source['target'])
                        assert pred['committed_at']<=feedback['revealed_at']<=update['completed_at']
                        reference_count+=1
                    else:assert not receipt.exists()
            if phase=='adaptation':
                frozen=load(d/'frozen_playbook.json')
                assert frozen['memory']==memory and frozen['memory_sha256']==digest(memory)
        assert len(list((d/'updates').glob('*.json')))==6
        case_count+=1
    cases=[c for c in plan['cells'] if c['seed']==42]
    assert case_count==len(cases) and update_count==6*len(cases)
    assert prediction_count==6*(len(cases)+sum(c['phase']=='offline' for c in cases))
    print(json.dumps(dict(passed=True,cases=case_count,development_predictions_including_training=prediction_count,
                         committed_updates=update_count,post_commit_gt_receipts=reference_count,
                         checkpoints_and_gt_order_verified=True,at=time.time())))


if __name__=='__main__':main()
