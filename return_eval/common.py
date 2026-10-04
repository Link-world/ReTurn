import json
from pathlib import Path
from datetime import datetime, timezone

def read(path):
    path=Path(path)
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []

def write(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)

def append(path,row):
    with Path(path).open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')

def now():return datetime.now(timezone.utc).isoformat()

def dependencies(row):
    ids=[]
    for m in row['messages']:
        if 'content_binding' in m:
            assert m['role']=='assistant' and m['content_binding']['kind']=='REQUEST_RAW'
            ids.append(m['content_binding']['request_id'])
    return ids

def resolve(row,cache,root):
    result=[]
    for m in row['messages']:
        if 'content_binding' in m:
            r=cache[m['content_binding']['request_id']]
            assert r['status']=='ok' and r['raw_text'].strip()
            result.append({'role':'assistant','content':[{'type':'text','text':r['raw_text']}]})
        else:
            assert m['role']=='user', 'Only native bound assistant history is permitted'
            parts=[]
            for part in m['content']:
                p=dict(part)
                if p['type'] in ('audio','video'):
                    kind=p['type']; path=(root/p[kind]).resolve()
                    if not path.is_file():raise FileNotFoundError(p[kind])
                    p[kind]=str(path)
                parts.append(p)
            result.append({'role':m['role'],'content':parts})
    return result
