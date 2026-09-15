"""Materialize future panels from validated, fixed split pools, without inference."""
from pathlib import Path
import argparse,hashlib,json,os,shutil
from core import atomic,digest,rows
from sizes import config,requested,sample,CORPORA,SPLITS,CONDITIONS


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(config_path,pool_root,out):
    settings=config(config_path);pool_root=Path(pool_root);out=Path(out)
    if out.resolve().is_relative_to(Path(__file__).resolve().parent):raise ValueError('Output must be outside the runner source directory')
    if out.exists():raise ValueError('Use a new output directory; existing experiment roots are immutable')
    # Input is an explicitly validated pool, not an arbitrary raw-data directory.
    audit_path=pool_root/'pool_manifest.json';audit=json.loads(audit_path.read_text())
    if audit.get('status')!='validated' or audit.get('cross_split_checks_passed') is not True:
        raise ValueError('Eligible pool needs a passed source/split/duplicate audit')
    prepared={};source_hashes={};actual={};selected_ids={}
    for corpus in CORPORA:
        prepared[corpus]={};actual[corpus]={};selected_ids[corpus]={}
        for split,n in requested(settings,corpus).items():
            relative=f'{corpus}/{split}.jsonl';path=pool_root/relative
            checksum=sha(path)
            if audit['files'].get(relative)!=checksum:raise ValueError('Eligible pool hash mismatch')
            source_hashes[relative]=checksum
            chosen=sample(rows(path),n,settings['sampling_seed'],corpus,split)
            if split=='dev' and len(chosen)<6:raise ValueError('Development validation requires at least six records')
            if split=='train' and corpus in ['dreaddit','goemotions'] and len(chosen)<8:
                raise ValueError('The unchanged ICL protocol needs at least eight training demonstrations')
            prepared[corpus][split]=chosen;actual[corpus][split]=len(chosen)
            selected_ids[corpus][split]=[r['record_id'] for r in chosen]
        # Recheck ID and exact-text leakage; the pinned input audit covers full-pool
        # source grouping, eligibility, privacy status and near-duplicate policy.
        prior_ids=set();prior_text=set()
        for split in SPLITS:
            selected=prepared[corpus][split]
            ids={r['record_id'] for r in selected}
            texts={' '.join(r['text'].casefold().split()) for r in selected}
            if len(texts)!=len(selected) or ids&prior_ids or texts&prior_text:
                raise ValueError('Selected panel has duplicate records or cross-split leakage')
            prior_ids|=ids;prior_text|=texts
    out.mkdir(parents=True,mode=0o700)
    files={}
    for corpus,parts in prepared.items():
        for split,selected in parts.items():
            path=out/'data'/corpus/(split+'.jsonl');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected));os.chmod(path,0o600)
            files[str(path.relative_to(out))]=sha(path)
    atomic(out/'dataset_sizes.json',settings)
    value=dict(protocol='four-corpus-v5-configurable-successor',requested=settings,counts=actual,
        selected_ids=selected_ids,files=files,pool_root=str(pool_root.resolve()),
        pool_manifest_sha256=sha(audit_path),pool_files=source_hashes,
        evaluation_scope='Previously eligible fixed split pools; all means every record in that eligible split, not all raw records or all splits combined.',
        full_panel_prediction_target=3*sum(CONDITIONS[c]*actual[c]['test'] for c in CORPORA),model_calls=0)
    value['manifest_sha256']=digest(value);atomic(out/'sampling_manifest.json',value)
    # Install the separate configurable runner bundle, never the active sealed code.
    source=Path(__file__).parent
    shutil.copytree(source,out/'code',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    return dict(counts=actual,full_panel_prediction_target=value['full_panel_prediction_target'],model_calls=0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True)
    p.add_argument('--pool-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.config,a.pool_root,a.out)))
