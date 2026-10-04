import json
import os
import time
import requests
from .common import now
from .media import Media

class Backend:
    def __init__(self,cfg,out):
        self.cfg=cfg;self.name=cfg['backend'];self.media=Media(out/'media_cache')
        prefix=cfg['env_prefix'];self.url=os.environ[prefix+'_BASE_URL'].rstrip('/')+'/chat/completions';self.key=os.environ[prefix+'_API_KEY']
        if not self.url.startswith('https://'):raise ValueError('API base URL must use HTTPS')
    def messages(self,conversations):
        result=[]
        for m in conversations:
            if m['role']=='assistant':
                result.append({'role':'assistant','content':'\n'.join(p['text'] for p in m['content'])});continue
            parts=[]
            for p in m['content']:
                kind=p['type']
                if kind=='text':parts.append(p)
                elif kind=='video' and self.name!='stepaudio_api':parts.append({'type':'video_url','video_url':{'url':self.media.data(p['video'],'video'),'fps':2}})
                elif kind=='audio' and self.name!='qwen37_api':
                    obj={'data':self.media.data(p['audio'],'audio')}
                    if self.name=='qwen38_api':obj['format']='wav'
                    parts.append({'type':'input_audio','input_audio':obj})
            if self.name=='stepaudio_api':
                assert sum(p['type']=='input_audio' for p in parts)==1
                parts.sort(key=lambda p:p['type']!='text')
            result.append({'role':'user','content':parts})
        return result
    def infer(self,messages):
        cfg=self.cfg;msgs=self.messages(messages);cap=cfg['max_tokens'];attempts=[];raw='';finish=None;usage=None;remote=None
        for attempt in range(cfg['attempts']):
            audit={'time_utc':now(),'attempt':attempt+1,'max_tokens':cap};started=time.monotonic();error=None
            try:
                payload={'model':cfg['model'],'messages':msgs,'temperature':0,'max_tokens':cap}
                stream=self.name=='qwen38_api'
                if stream:payload.update(modalities=['text'],stream=True,stream_options={'include_usage':True},reasoning_effort='none')
                if self.name=='qwen37_api':payload['enable_thinking']=False
                with requests.post(self.url,headers={'Authorization':'Bearer '+self.key},json=payload,timeout=(20,240),stream=stream,allow_redirects=False) as response:
                    audit.update(http_status=response.status_code,request_id=response.headers.get('x-request-id'))
                    if response.status_code!=200:
                        error='http_'+str(response.status_code)
                    elif stream:
                        raw='';finish=None;done=False
                        for line in response.iter_lines():
                            if not line or not line.startswith(b'data:'):continue
                            body=line[5:].strip()
                            if body==b'[DONE]':done=True;break
                            obj=json.loads(body);remote=obj.get('id',remote);usage=obj.get('usage') or usage
                            for c in obj.get('choices',[]):
                                raw+=c.get('delta',{}).get('content') or ''
                                finish=c.get('finish_reason') or finish
                        if not done and finish is None:error='incomplete_stream'
                    else:
                        obj=response.json();remote=obj.get('id');usage=obj.get('usage');c=obj['choices'][0];raw=c['message'].get('content') or '';finish=c.get('finish_reason')
                if not error:
                    if finish=='length':error='length_truncated'
                    elif not raw.strip():error='empty_response'
                    elif finish not in ('stop',):error='finish_'+str(finish)
            except Exception as e:error=type(e).__name__ # Avoid logging credentials, URLs or response bodies.
            audit.update(error=error,elapsed_s=round(time.monotonic()-started,3));attempts.append(audit)
            if error is None:break
            if error in ('http_401','http_403','http_451','http_400') or error.startswith('finish_'):break
            if error=='length_truncated':
                if cap==cfg['retry_tokens']:break
                cap=cfg['retry_tokens']
            if attempt+1<cfg['attempts']:time.sleep(min(2**attempt,16))
        return dict(raw_text=raw,status='ok' if error is None else 'error',error=error,finish_reason=finish,usage=usage,response_id=remote,decode_max_tokens=cap,attempts=attempts,endpoint=self.url)
