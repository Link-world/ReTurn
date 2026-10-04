"""CPU structural checks; --media additionally checks actual file availability."""
import argparse,json
from pathlib import Path
from collections import Counter,defaultdict
from .common import read,dependencies

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--media',action='store_true');ap.add_argument('--manifest',type=Path);a=ap.parse_args();root=a.root
    tasks=read(root/'data/tasks/tasks.jsonl');inputs=read(root/'data/tasks/inputs.jsonl');answers=read(root/'data/tasks/answers.jsonl');media=json.loads((root/'data/media_manifest.json').read_text());manifest=json.loads((root/'data/preview_manifest.json').read_text())
    assert len(tasks)==80 and len({t['task_id'] for t in tasks})==80
    assert set(manifest['task_ids'])=={t['task_id'] for t in tasks}
    pairs=defaultdict(list)
    for t in tasks:
        assert t['split']=='DEVELOPMENT' and t['adapt_split'] in ['ADAPT_TRAIN','ADAPT_VAL']
        pairs[t['pair_id']].append(t)
    assert len(pairs)==40
    cells=Counter()
    for rs in pairs.values():
        assert len(rs)==2;assert {r['operation'] for r in rs} in [{'preserve','revise'},{'retrieve','rebind'}]
        t=rs[0];cell=(t['history_side'],t['required_modality'],t['history_horizon']);assert all((r['history_side'],r['required_modality'],r['history_horizon'])==cell for r in rs);cells[cell]+=1
    assert len(cells)==8 and set(cells.values())=={5}
    rows={r['request_id']:r for r in inputs};ans={r['request_id']:r for r in answers};assert len(rows)==len(inputs) and len(ans)==len(answers)
    paths={r[k] for r in media for k in ['video','audio']};refs=set()
    for r in inputs:
        assert not {'gold','aliases','choices'}&r.keys()
        for d in dependencies(r):assert d in rows
        for m in r['messages']:
            if m['role']=='assistant':assert 'content_binding' in m and 'content' not in m
            for p in m.get('content',[]):
                if p['type'] in ['video','audio']:
                    path=p[p['type']];assert path in paths and not Path(path).is_absolute() and '..' not in Path(path).parts;refs.add(path)
    assert paths==refs
    for t in tasks:
        assert set(t['views'])=={'openqa','mcq'}
        for interface,v in t['views'].items():
            for k in ['control_request_id','history_request_id']:
                rid=v[k];assert rid in rows and rid in ans;assert ans[rid]['interface']==interface
                if interface=='mcq':assert ans[rid]['gold'] in list('ABCD') and len(ans[rid]['choices'])==4
            assert dependencies(rows[v['history_request_id']])==v['native_dependency_request_ids']
    for fn in ['quickstart_manifest.json','long_validation_manifest.json']:
        ids=json.loads((root/'data'/fn).read_text())['task_ids'];assert len(ids)==8
        assert set(Counter(t['pair_id'] for t in tasks if t['task_id'] in ids).values())=={2}
    checked_paths=paths
    if a.manifest:
        selected_ids=json.loads(a.manifest.read_text())['task_ids']
        if not selected_ids or len(selected_ids)!=len(set(selected_ids)):
            ap.error('Manifest task_ids must be nonempty and unique')
        selected=set(selected_ids)
        if not selected<={t['task_id'] for t in tasks}:
            ap.error('Manifest contains unknown task IDs')
        needed=set()
        def visit(k):
            if k in needed:return
            needed.add(k)
            for d in dependencies(rows[k]):visit(d)
        for t in tasks:
            if t['task_id'] in selected:
                for v in t['views'].values():visit(v['control_request_id']);visit(v['history_request_id'])
        checked_paths={p[p['type']] for k in needed for m in rows[k]['messages'] for p in m.get('content',[]) if p['type'] in ['audio','video']}
    missing=[p for p in sorted(checked_paths) if not (root/p).is_file()]
    print(json.dumps({'base_tasks':len(tasks),'complete_pairs':len(pairs),'strata':len(cells),'pairs_per_stratum':5,'requests_including_native':len(rows),'media_clips':len(media),'checked_media_files':len(checked_paths),'missing_media_files':len(missing)}))
    if a.media and missing:raise SystemExit(2)
if __name__=='__main__':main()
