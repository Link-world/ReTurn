"""Formal rule + blinded GPT-medium review; unresolved reviews remain unscored."""
import argparse,json,os,re
from pathlib import Path
from .common import read,write,append,now
from .formal import SYSTEM,norm,mcq_rule

def prepare(answer,raw):
    gold=answer['gold'];aliases=list(dict.fromkeys([gold,*answer.get('aliases',[])]));interface=answer['interface'];q=answer['scoring_question']
    strict=raw.strip().upper()==gold.upper() if interface=='mcq' else norm(raw) in {norm(v) for v in aliases}
    rule=bool(strict or interface=='mcq' and mcq_rule(raw,gold,answer.get('choices',[])))
    parts=[q,gold,aliases,answer.get('choices',[]),interface,raw]
    if interface=='openqa' and re.search(r'\bcolou?r\b',q,re.I):parts.append('question_requested_color_granularity_v1')
    identity=json.dumps(parts,ensure_ascii=False,separators=(',',':'))
    item={'question':q,'gold':gold,'aliases':aliases,'options':answer.get('choices',[]),'candidate':raw,'answer_type':interface}
    return strict,rule,identity,item

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--cache',action='append',type=Path,default=[]);ap.add_argument('--judge',action='store_true');a=ap.parse_args();out=a.run/'scoring';out.mkdir(exist_ok=True)
    answers={r['request_id']:r for r in read(a.root/'data/tasks/answers.jsonl')};outputs={r['request_id']:r for r in read(a.run/'predictions.jsonl')}
    contract=json.loads((a.run/'run_contract.json').read_text());selected={r['request_id'] for r in contract['inputs'] if r['request_id'] in answers}
    cache={r['identity']:r['judgment'] for path in [*a.cache,out/'review_cache.jsonl'] for r in read(path)};pending={};records=[]
    for k in sorted(selected):
        r=outputs.get(k,{'status':'missing','error':'missing','raw_text':''});row=dict(answers[k],raw_text=r['raw_text'],status=r['status'],error=r.get('error'))
        if r['status']=='ok':
            strict,rule,identity,item=prepare(answers[k],r['raw_text']);row.update(strict_correct=strict,rule_correct=rule,review_identity=None if rule else identity)
            if not rule and identity not in cache:pending.setdefault(identity,dict(item,id=f'item-{len(pending):06d}'))
        records.append(row)
    if a.judge and pending:
        import requests
        url=os.environ['JUDGE_BASE_URL'].rstrip('/')+'/chat/completions';model=os.environ.get('JUDGE_MODEL','gpt-5.6-sol');key=os.environ['JUDGE_API_KEY']
        if not url.startswith('https://'):raise ValueError('Judge base URL must use HTTPS')
        items=list(pending.items())
        for offset in range(0,len(items),20):
            chunk=items[offset:offset+20];audit={'time_utc':now(),'model':model,'endpoint':url,'requested_reasoning_effort':'medium','items':len(chunk)}
            try:
                response=requests.post(url,headers={'Authorization':'Bearer '+key},json={'model':model,'reasoning_effort':'medium','max_completion_tokens':5000,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'items':[v for _,v in chunk]},ensure_ascii=False)}]},timeout=240,allow_redirects=False)
                audit.update(http_status=response.status_code,request_id=response.headers.get('x-request-id'))
                response.raise_for_status();body=response.json();raw=body['choices'][0]['message']['content'];js=json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())['judgments']
                assert len(js)==len(chunk) and {j['id'] for j in js}=={v['id'] for _,v in chunk}
                lookup={v['id']:identity for identity,v in chunk}
                for j in js:
                    assert j['verdict'] in ['equivalent','incorrect','uncertain'] and isinstance(j['format_compliant'],bool) and isinstance(j['reason'],str)
                for j in js:
                    identity=lookup[j['id']];cache[identity]=j;append(out/'review_cache.jsonl',{'identity':identity,'judgment':j,'judge_model':model,'requested_reasoning_effort':'medium'})
                audit.update(status='ok',usage=body.get('usage'),response_id=body.get('id'))
            except Exception as e:audit.update(status='error',error=type(e).__name__)
            append(out/'judge_audit.jsonl',audit)
    missing=0
    for r in records:
        identity=r.pop('review_identity',None);j=cache.get(identity)
        if r['status']!='ok':r['score_status']='inference_failed'
        elif not r['rule_correct'] and not j:r['score_status']='review_pending';missing+=1
        else:
            r.update(score_status='scored',content_correct=bool(r['rule_correct'] or j['verdict']=='equivalent'),uncertain=bool(j and j['verdict']=='uncertain'),format_compliant=True if r['rule_correct'] else j['format_compliant'],review_reason=None if r['rule_correct'] else j['reason'])
    target=out/'scored_records.jsonl';target.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records));write(out/'summary.json',{'requests':len(records),'scored':sum(r['score_status']=='scored' for r in records),'review_pending':missing,'inference_failed':sum(r['score_status']=='inference_failed' for r in records)})
    print((out/'summary.json').read_text().strip())
    if missing or any(r['score_status']=='inference_failed' for r in records):raise SystemExit(2)
if __name__=='__main__':main()
