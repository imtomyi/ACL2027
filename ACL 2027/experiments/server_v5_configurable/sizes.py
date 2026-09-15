"""Single source of sample counts for future runs; never mutate sealed v5 panels."""
from pathlib import Path
import hashlib,json

CORPORA=('dreaddit','goemotions','cache','parlamint_gb')
SPLITS=('train','dev','test')
CONDITIONS={'dreaddit':10,'goemotions':10,'cache':4,'parlamint_gb':4}


def config(path):
    value=json.loads(Path(path).read_text())
    if set(value)!={'schema_version','sampling_seed','defaults','overrides'} or value['schema_version']!=1:
        raise ValueError('Unsupported dataset-size configuration')
    if type(value['sampling_seed'])!=int:raise ValueError('sampling_seed must be an integer')
    if set(value['defaults'])!=set(SPLITS) or set(value['overrides'])-set(CORPORA):
        raise ValueError('Unknown or missing dataset/split')
    for override in value['overrides'].values():
        if not isinstance(override,dict) or set(override)-set(SPLITS):raise ValueError('Unknown override split')
    for corpus in CORPORA:
        for size in requested(value,corpus).values():
            if size!='all' and (type(size)!=int or size<1):raise ValueError('Sizes must be positive integers or "all"')
    return value


def requested(value,corpus):
    return dict(value['defaults'],**value['overrides'].get(corpus,{}))


def manifest(root):
    p=Path(root)/'sampling_manifest.json';v=json.loads(p.read_text())
    expected=v['manifest_sha256'];body={k:x for k,x in v.items() if k!='manifest_sha256'}
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if actual!=expected:raise ValueError('Sampling manifest changed')
    return v


def counts(root,corpus):return manifest(root)['counts'][corpus]


def panel_target(root,seeds=(42,43,44)):
    return len(seeds)*sum(CONDITIONS[c]*counts(root,c)['test'] for c in CORPORA)


def cell_sizes(root,corpus,phase,method):
    n=counts(root,corpus)
    return dict(n=n['test'],train_n=n['train'],dev_n=n['dev'],
                update_n=(n['train'] if phase=='offline' else n['test']) if method in ['ace','dc_cu'] else 0)


def sample(rows,n,seed,corpus,split):
    """Canonical eligible split pool in, deterministic sample out. Never silently cap."""
    seen=set();ranked=[]
    for row in rows:
        rid=row['record_id']
        if rid in seen:raise ValueError('Duplicate record ID in eligible pool')
        if not isinstance(row.get('text'),str) or not row['text'].strip():raise ValueError('Missing source text')
        seen.add(rid)
        key=hashlib.sha256(f'sample:{seed}:{corpus}:{split}:{rid}'.encode()).hexdigest()
        ranked.append((key,rid,row))
    ranked.sort(key=lambda x:(x[0],x[1]))
    if n!='all' and len(ranked)<n:
        raise ValueError(f'{corpus}/{split}: requested {n}, but eligible pool has {len(ranked)}; supply a larger validated source pool')
    chosen=ranked if n=='all' else ranked[:n]
    if not chosen:raise ValueError('Empty eligible split')
    return [r for _,_,r in chosen]
