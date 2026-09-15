"""Prepare real, source-disjoint v5 panels without model calls or source text logging."""
from pathlib import Path
import argparse, collections, csv, hashlib, heapq, itertools, json, os, re, tarfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'four-corpus-server-v5'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def read(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2)+'\n');os.chmod(tmp,0o600);tmp.replace(p)
def text_key(r):return digest(' '.join(r['text'].casefold().split()))
def rank(split,r):return digest(f'{PROTOCOL}:42:{split}:{r["record_id"]}')
def shingles(r):
    t=re.findall(r'\w+',r['text'].casefold())
    return set(zip(*(t[i:] for i in range(5)))) if len(t)>=5 else {tuple(t)}
def near(a,b):return bool(a and b) and len(a&b)/len(a|b)>=.9

def select(rows,split,previous):
    prior=[r for part in previous for r in part]
    groups={r.get('source_id') for r in prior if r.get('source_id')}
    seen={text_key(r) for r in prior};ids={r['record_id'] for r in prior}
    prior_shingles=[shingles(r) for r in prior]
    out=[];excluded=collections.Counter()
    for r in sorted(rows,key=lambda r:rank(split,r)):
        if r.get('source_id') and r['source_id'] in groups:excluded['source_group_overlap']+=1;continue
        if r['record_id'] in ids or text_key(r) in seen:excluded['exact_duplicate']+=1;continue
        s=shingles(r)
        if any(near(s,t) for t in prior_shingles):excluded['cross_split_near_duplicate']+=1;continue
        out.append(r);seen.add(text_key(r));ids.add(r['record_id'])
        if len(out)==100:break
    if len(out)!=100:raise ValueError(f'{split}: only {len(out)} eligible records remain')
    return out,dict(excluded)

def historical(c):
    p=ROOT/'Storage/online100/run_20260914_uniform'/c/'data/test.jsonl'
    rows=read(p)
    if len(rows)!=100:raise ValueError('Historical evaluation count mismatch')
    return rows,p

def base_row(x,target=None):
    r={k:x[k] for k in ['record_id','source_id','text'] if k in x}
    if target is not None:r['target']=target
    return r

def make(c,out):
    old,oldpath=historical(c);sources={str(oldpath):sha(oldpath)};notes=[];excluded={}
    if c=='dreaddit':
        source=ROOT/'dataset/deidentified/dreaddit/records.jsonl'
        prep=ROOT/'Storage/dreaddit_icl/comparison_preparation_20260912/splits.json'
        m=json.loads(prep.read_text());assert sha(source)==m['source_sha256']
        allrows={x['record_id']:x for x in read(source)}
        pools={k:[base_row(allrows[i],[int(allrows[i]['sampling_strata']['stress_label'])]) for i in ids if allrows[i]['quality']['eligible_for_packet_sampling']] for k,ids in m['ids'].items()}
        byid={r['record_id']:r for r in pools['test']}
        test=[]
        for x in old:
            r=byid[x['record_id']];assert x['text']==r['text'] and x['target']==r['target'];test.append(r)
        train,excluded['train']=select(pools['train'],'train',[test])
        dev,excluded['dev']=select(pools['validation'],'dev',[test,train])
        sources.update({str(source):sha(source),str(prep):sha(prep)})
        notes.append('Preserve prior eligibility, duplicate/date quarantine and official split manifest; source_id groups are posts, not verified authors.')
    elif c=='goemotions':
        source=ROOT/'dataset/raw/goemotions/upstream';labels=(source/'emotions.txt').read_text().splitlines();assert len(labels)==28
        neutral=labels.index('neutral');pools={}
        for split in ['train','dev','test']:
            p=source/(split+'.tsv');sources[str(p)]=sha(p)
            with p.open() as f:rows=[dict(record_id=x[2],text=x[0],target=sorted(map(int,x[1].split(',')))) for x in csv.reader(f,delimiter='\t')]
            pools[split]=[x for x in rows if x['target'] and len(x['target'])==len(set(x['target'])) and all(0<=i<28 for i in x['target'])]
            excluded[split+'_invalid_reference']=len(rows)-len(pools[split])
        byid={r['record_id']:r for r in pools['test']};test=[]
        for x in old:
            r=byid[x['record_id']];assert x['text']==r['text'] and x['target']==r['target'];test.append(r)
        train,excluded['train']=select(pools['train'],'train',[test]);dev,excluded['dev']=select(pools['dev'],'dev',[test,train])
        sources[str(source/'emotions.txt')]=sha(source/'emotions.txt')
        notes.append('Official neutral-plus-emotion reference combinations are valid; never remove or rewrite GT. Execution amendment v5-preflight-r1. Official comment-ID splits; author/thread grouping is unavailable in these TSV files. Source-disjointness beyond comment IDs cannot be certified.')
    elif c=='cache':
        source=ROOT/'dataset/deidentified/agyw_focus_groups/records.jsonl';rows=read(source)
        valid=[x for x in rows if x['quality']['eligible_for_packet_sampling']]
        byid={r['record_id']:r for r in valid};test=[]
        for x in old:
            r=base_row(byid[x['record_id']]);assert x==r;test.append(r)
        groups={r['source_id'] for r in test}
        available=sorted({x['source_id'] for x in valid}-groups,key=lambda x:digest(PROTOCOL+':dev-group:'+x))
        # Partition whole remaining sessions before selecting records, independent of labels/results.
        if len(available)<2:raise ValueError('Not enough independent sessions for train/dev')
        devgroups=set(available[:max(1,len(available)//3)])
        train,excluded['train']=select([base_row(x) for x in valid if x['source_id'] not in devgroups],'train',[test])
        dev,excluded['dev']=select([base_row(x) for x in valid if x['source_id'] in devgroups],'dev',[test,train])
        sources[str(source)]=sha(source)
        notes.append('Eligible deidentified participant turns only; split by whole session. Cross-session participant linkage unavailable. Mechanical eligibility does not constitute manual privacy clearance.')
        excluded['manual_review_required_in_selected']=sum(byid[x['record_id']]['quality'].get('manual_excerpt_review_required',False) for x in test+train+dev)
    else:
        source=ROOT/'dataset/raw/parlamint_gb/ParlaMint-GB.tgz';test=old
        testgroups={r['source_id'] for r in test};byid={x['record_id']:x for x in test};verified=set()
        candidates={'train':[],'dev':[]};counts=collections.Counter();docs=0
        # Keep 1000 lowest-ID-hash candidates per role. This is a bounded candidate inventory,
        # not a substitute panel if exclusions prevent reaching the required 100.
        with tarfile.open(source,'r|gz') as archive:
            for member in archive:
                if not member.isfile() or '/ParlaMint-GB_' not in member.name or not member.name.endswith('.xml'):continue
                group=Path(member.name).stem;root=ET.parse(archive.extractfile(member)).getroot();docs+=1
                split='dev' if int(digest(PROTOCOL+':dev-group:'+group),16)%3==0 else 'train'
                for idx,u in enumerate(root.iter()):
                    if u.tag.split('}')[-1]!='u':continue
                    text=' '.join(' '.join(' '.join(s.itertext()) for s in u.iter() if s.tag.split('}')[-1]=='seg').split())
                    if not 30<=len(text.split())<=800:continue
                    r=dict(record_id=group+':'+str(idx),source_id=group,text=text)
                    if r['record_id'] in byid:
                        assert r==byid[r['record_id']];verified.add(r['record_id'])
                    if group in testgroups:continue
                    counts[split]+=1;k=-int(rank(split,r),16);h=candidates[split];entry=(k,r['record_id'],r)
                    if len(h)<1000:heapq.heappush(h,entry)
                    elif k>h[0][0]:heapq.heapreplace(h,entry)
                if docs%500==0:print(json.dumps({'dataset':c,'scanned_documents':docs}),flush=True)
        assert len(verified)==100,'Could not verify every historical evaluation record against XML'
        train,excluded['train']=select([v[2] for v in candidates['train']],'train',[test])
        dev,excluded['dev']=select([v[2] for v in candidates['dev']],'dev',[test,train])
        sources[str(source)]=sha(source);excluded['eligible_population']=dict(counts)
        notes.append('Document-disjoint speech excerpts, 30–800 words with no truncation. Recurring speakers may span sessions. Candidate inventory capped at 1000 per role by ID hash.')
    parts={'train':train,'dev':dev,'test':test}
    for name,rows in parts.items():
        assert len(rows)==len({r['record_id'] for r in rows})==100
        assert len({text_key(r) for r in rows})==100,f'Exact duplicate within {c}/{name}'
    pairs={}
    for a,b in itertools.combinations(parts,2):
        ra,rb=parts[a],parts[b]
        ids=set(x['record_id'] for x in ra)&set(x['record_id'] for x in rb)
        groups=set(x['source_id'] for x in ra if x.get('source_id'))&set(x['source_id'] for x in rb if x.get('source_id'))
        exact=set(text_key(x) for x in ra)&set(text_key(x) for x in rb)
        near_count=sum(near(shingles(x),shingles(y)) for x in ra for y in rb)
        assert not(ids or groups or exact or near_count),f'Cross-split overlap {c}/{a}/{b}'
        pairs[a+'__'+b]={'id_overlap':len(ids),'source_group_overlap':len(groups),'normalized_exact_overlap':len(exact),'near_duplicate_pairs':near_count}
    dest=out/c;dest.mkdir(parents=True,exist_ok=True)
    if (dest/'manifest.json').exists():raise ValueError('Prepared panel exists; do not overwrite')
    hashes={}
    for split,rows in parts.items():
        p=dest/(split+'.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));os.chmod(p,0o600);hashes[split]=sha(p)
    manifest=dict(protocol=PROTOCOL,dataset=c,status='prepared_pending_independent_audit',counts={k:len(v) for k,v in parts.items()},sources=sources,files=hashes,selected_ids={k:[r['record_id'] for r in v] for k,v in parts.items()},groups={k:sorted({r['source_id'] for r in v if r.get('source_id')}) for k,v in parts.items()},cross_split_checks=pairs,exclusions=excluded,notes=notes,evaluation_panel='Previously observed historical panel; preserved IDs/text/order; not untouched confirmatory test',near_duplicate_rule='Casefold Unicode word 5-gram set Jaccard >=0.9; shorter texts use full word tuple',model_calls=0)
    write(dest/'manifest.json',manifest)
    print(json.dumps({'dataset':c,'counts':manifest['counts'],'status':manifest['status'],'model_calls':0}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['dreaddit','goemotions','cache','parlamint_gb'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.dataset,a.out)
