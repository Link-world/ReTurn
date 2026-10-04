"""Run frozen requests in dependency order, with native same-backend history."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from .common import read,write,append,now,dependencies,resolve

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True,type=Path);ap.add_argument('--manifest',default='data/quickstart_manifest.json',type=Path);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--out',required=True,type=Path);ap.add_argument('--interfaces',nargs='+',choices=['openqa','mcq'],default=['openqa','mcq']);ap.add_argument('--retry-errors',action='store_true');a=ap.parse_args()
    cfg=json.loads(a.config.read_text());root=a.root.resolve();out=a.out;out.mkdir(parents=True,exist_ok=True)
    tasks={r['task_id']:r for r in read(root/'data/tasks/tasks.jsonl')};rows={r['request_id']:r for r in read(root/'data/tasks/inputs.jsonl')}
    chosen=json.loads(a.manifest.read_text())['task_ids'];active=[tasks[k] for k in chosen if tasks[k]['required_modality'] in cfg['modalities']]
    if not active:raise ValueError('No tasks match the selected model modalities')
    final=set()
    for task in active:
        for i in a.interfaces:
            v=task['views'][i];final.update([v['control_request_id'],v['history_request_id']])
    required=set();visiting=set();order=[]
    def visit(k):
        if k in required:return
        if k in visiting:raise ValueError('Dependency cycle')
        visiting.add(k)
        for d in dependencies(rows[k]):visit(d)
        visiting.remove(k);required.add(k);order.append(k)
    for k in sorted(final):visit(k)
    # Verify media before loading a backend or trusting cached replies.
    expected=json.loads((root/'data/media_checksums.json').read_text())
    media_paths=sorted({p[p['type']] for k in required for m in rows[k]['messages'] for p in m.get('content',[]) if p['type'] in ('audio','video')})
    missing=[name for name in media_paths if not (root/name).is_file()]
    if missing:raise ValueError(f'Missing {len(missing)} media files. Install the companion archive with scripts/install_media.py before inference.')
    verified={}
    for name in media_paths:
        path=(root/name).resolve()
        if not path.is_relative_to(root):raise ValueError('Media path escapes repository')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if expected.get(name)!=digest:raise ValueError('Frozen media checksum mismatch: '+name)
        verified[name]=digest
    # Config, frozen requests and media identities define a resumable run.
    contract={'config':cfg,'endpoint':os.environ.get(cfg['env_prefix']+'_BASE_URL'),'model_location':os.environ.get(cfg['env_prefix']+'_MODEL'),'inputs':[rows[k] for k in sorted(required)],'task_ids':[t['task_id'] for t in active],'interfaces':a.interfaces}
    contract['media_sha256']=verified
    cp=out/'run_contract.json'
    if cp.exists() and json.loads(cp.read_text())!=contract:raise ValueError('Output directory belongs to a different run contract; choose a new --out')
    write(cp,contract)
    latest={r['request_id']:r for r in read(out/'predictions.jsonl')};cache={k:r for k,r in latest.items() if r['status']=='ok'}
    def state(status):write(out/'state.json',{'status':status,'pid':os.getpid(),'expected':len(required),'complete':len(required&cache.keys()),'failed':sum(latest.get(k,{}).get('status')=='error' for k in required),'blocked':sum(latest.get(k,{}).get('status')=='blocked' for k in required),'time_utc':now()})
    state('loading');backend=None
    for k in order:
        if k in cache:continue
        prior=latest.get(k,{})
        if prior.get('status')=='error' and (not a.retry_errors or prior.get('error') in ('http_451','finish_content_filter')):continue
        bad=[d for d in dependencies(rows[k]) if d not in cache]
        if bad:r={'status':'blocked','error':'dependency_failed','blocked_by':bad,'raw_text':''}
        else:
            started=time.monotonic()
            try:
                messages=resolve(rows[k],cache,root)
                if backend is None:
                    if cfg['kind']=='api':from .api import Backend
                    else:from .local import Backend
                    backend=Backend(cfg,out)
                r=backend.infer(messages)
                r['user_turns']=sum(m['role']=='user' for m in messages)
                r['native_history']=[{'request_id':d,'raw_text':cache[d]['raw_text']} for d in dependencies(rows[k])]
                r['contract_media_counts']={kind:sum(p['type']==kind for m in messages for p in m['content']) for kind in ['audio','video']}
                r['consumed_media_counts']={kind:count for kind,count in r['contract_media_counts'].items() if not (kind=='audio' and cfg['backend'] in ['qwen37_api','qwen3_vl'] or kind=='video' and cfg['backend'] in ['stepaudio_api','audio_flamingo3'])}
            except Exception as e:r={'status':'error','error':type(e).__name__,'raw_text':''};write(out/'last_local_error.json',{'request_id':k,'type':type(e).__name__,'detail':str(e)[:1000]})
            r['elapsed_s']=round(time.monotonic()-started,3)
        r.update(request_id=k,backend=cfg['backend'],model=cfg['model'],time_utc=now(),is_final=k in final)
        append(out/'predictions.jsonl',r);latest[k]=r
        if r['status']=='ok':cache[k]=r
        state('running')
    state('complete' if required<=cache.keys() else 'incomplete');print(json.dumps(json.loads((out/'state.json').read_text())))
    if not required<=cache.keys():raise SystemExit(2)
if __name__=='__main__':main()
