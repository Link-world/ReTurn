"""Paired preview subset results; separate interfaces and shared valid C/H0 denominator."""
import argparse,json,csv
from pathlib import Path
from collections import defaultdict,Counter
from .common import read,write
from .formal import chstats

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--root',type=Path,default=Path('.'));a=ap.parse_args();out=a.run/'report';out.mkdir(exist_ok=True)
    cfg=json.loads((a.run/'run_contract.json').read_text());tasks={r['task_id']:r for r in read(a.root/'data/tasks/tasks.jsonl')};scores={r['request_id']:r for r in read(a.run/'scoring/scored_records.jsonl')};items=[];excluded=[]
    for k in cfg['task_ids']:
        t=tasks[k]
        for i in cfg['interfaces']:
            v=t['views'][i];c=scores.get(v['control_request_id'],{});h=scores.get(v['history_request_id'],{})
            base={key:t[key] for key in ['task_id','pair_id','operation','history_side','required_modality','history_horizon','adapt_split','family']};base['interface']=i
            if c.get('score_status')!='scored' or h.get('score_status')!='scored':
                excluded.append(dict(base,reason='single:'+c.get('score_status','missing')+';multi:'+h.get('score_status','missing')));continue
            items.append(dict(base,single=bool(c['content_correct']),multi=bool(h['content_correct']),single_strict=bool(c['strict_correct']),multi_strict=bool(h['strict_correct'])))
    groups=defaultdict(list)
    for r in items:
        i=r['interface'];groups[('interface',i,i)].append(r)
        for field in ['operation','required_modality','history_horizon','history_side','adapt_split']:
            groups[(field,str(r[field]),i)].append(r)
        groups[('operation×modality×horizon','/'.join(r[k] for k in ['operation','required_modality','history_horizon']),i)].append(r)
    summary=[]
    for (field,value,i),rs in sorted(groups.items()):
        metrics=chstats([{'C':{'content_correct':r['single']},'H0':{'content_correct':r['multi']}} for r in rs]);n=metrics['n'];c=metrics['C_correct'];h=metrics['H0_correct']
        summary.append(dict(group=field,value=value,interface=i,n=n,single_accuracy=metrics['C_pct'],multi_accuracy=metrics['H0_pct'],delta_conv_pp=metrics['gap_pp'],harm=metrics['harm'],rescue=metrics['rescue'],single_strict=100*sum(r['single_strict'] for r in rs)/n,multi_strict=100*sum(r['multi_strict'] for r in rs)/n))
    # Formal paired-operation denominator: reference and conflict must both have C and H0.
    pairgroups=defaultdict(dict);pair_sides={}
    for tid in cfg['task_ids']:
        for i in cfg['interfaces']:
            key=(tasks[tid]['pair_id'],i);pairgroups[key];pair_sides[key]=tasks[tid]['history_side']
    for r in items:pairgroups[(r['pair_id'],r['interface'])][r['operation']]=r
    pairrows=[];pair_missing=[]
    for (pid,i),rs in pairgroups.items():
        ops=('preserve','revise') if pair_sides[(pid,i)]=='task' else ('retrieve','rebind')
        if not all(k in rs for k in ops):pair_missing.append({'pair_id':pid,'interface':i,'reason':'missing_reference_or_conflict'});continue
        ref,conf=[rs[k] for k in ops]
        pairrows.append(dict(pair_id=pid,interface=i,reference_task_id=ref['task_id'],conflict_task_id=conf['task_id'],history_side=ref['history_side'],required_modality=ref['required_modality'],history_horizon=ref['history_horizon'],reference_single=ref['single'],conflict_single=conf['single'],reference_multi=ref['multi'],conflict_multi=conf['multi']))
    pg=defaultdict(list)
    for r in pairrows:pg[(r['interface'],r['history_side'])].append(r)
    four=[]
    for (i,side),rs in sorted(pg.items()):
        for cond in ['single','multi']:
            n=len(rs);cells=Counter((r['reference_'+cond],r['conflict_'+cond]) for r in rs)
            four.append(dict(interface=i,history_side=side,condition=cond,pairs=n,both_correct=cells[(True,True)],reference_only=cells[(True,False)],conflict_only=cells[(False,True)],both_wrong=cells[(False,False)],reference_minus_conflict_pp=100*(cells[(True,False)]-cells[(False,True)])/n))
    write(out/'summary.json',{'label':'preview subset results','model':cfg['config']['model'],'logical_views_expected':len(cfg['task_ids'])*len(cfg['interfaces']),'valid_single_multi_views':len(items),'excluded_views':len(excluded),'expected_operation_pair_views':len(pairgroups),'excluded_operation_pair_views':len(pair_missing),'unique_base_tasks':len({r['task_id'] for r in items}),'exclusion_reasons':dict(Counter(r['reason'] for r in excluded)),'groups':summary,'paired_operation_four_cells':four})
    for name,rs in [('paired_items',items),('excluded_items',excluded),('operation_pairs',pairrows),('excluded_pairs',pair_missing)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rs))
    fields=['group','value','interface','n','single_accuracy','multi_accuracy','delta_conv_pp','harm','rescue','single_strict','multi_strict']
    with (out/'groups.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(summary)
    print(json.dumps({'label':'preview subset results','valid':len(items),'excluded':len(excluded),'complete_operation_pairs':len(pairrows)}))
    if excluded or pair_missing:raise SystemExit(2)
if __name__=='__main__':main()
