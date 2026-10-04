import os
import torch
from .media import Media

class Backend:
    def __init__(self,cfg,out):
        self.cfg=cfg;self.name=cfg['backend'];self.media=Media(out/'media_cache');path=os.environ.get(cfg['env_prefix']+'_MODEL',cfg['model'])
        torch.set_num_threads(4);torch.manual_seed(cfg['seed'])
        from transformers import AutoProcessor
        kw=dict(dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='sdpa')
        if self.name=='qwen3_omni':
            from transformers import Qwen3OmniMoeForConditionalGeneration,Qwen3OmniMoeProcessor
            kw['attn_implementation']='flash_attention_2'
            self.model=Qwen3OmniMoeForConditionalGeneration.from_pretrained(path,**kw).eval();self.model.disable_talker()
            self.processor=Qwen3OmniMoeProcessor.from_pretrained(path)
        elif self.name=='qwen3_vl':
            from transformers import Qwen3VLMoeForConditionalGeneration
            self.model=Qwen3VLMoeForConditionalGeneration.from_pretrained(path,**kw).eval();self.processor=AutoProcessor.from_pretrained(path);self.processor.tokenizer.padding_side='left'
        else:
            from transformers import AudioFlamingo3ForConditionalGeneration
            from .audio_processor import load_processor
            self.model=AudioFlamingo3ForConditionalGeneration.from_pretrained(path,**kw).eval();self.processor=load_processor(path)
    def prepare(self,messages):
        conv=[];videos=[];metadata=[]
        for m in messages:
            parts=[]
            for p in m['content']:
                kind=p['type']
                if self.name=='qwen3_vl' and kind=='audio' or self.name=='audio_flamingo3' and kind=='video':continue
                if self.name=='qwen3_vl' and kind=='video':
                    frames,fps,indices,n=self.media.frames(p['video']);videos.append(frames);metadata.append(dict(fps=fps,total_num_frames=n,frames_indices=indices.tolist()));parts.append({'type':'video','path':p['video']})
                elif self.name=='audio_flamingo3' and kind=='audio':parts.append({'type':'audio','path':p['audio']})
                else:parts.append(p)
            conv.append({'role':m['role'],'content':parts})
        p=self.processor
        if self.name=='qwen3_omni':
            from qwen_omni_utils import process_mm_info
            audio,images,vid=process_mm_info(conv,use_audio_in_video=False)
            return p(text=p.apply_chat_template(conv,tokenize=False,add_generation_prompt=True),audio=audio,images=images,videos=vid,return_tensors='pt',padding=True,use_audio_in_video=False)
        if self.name=='qwen3_vl':
            return p(text=[p.apply_chat_template(conv,tokenize=False,add_generation_prompt=True)],videos=videos,video_metadata=metadata,videos_kwargs={'do_sample_frames':False},text_kwargs={'padding':True},return_tensors='pt')
        batch=p.apply_chat_template([conv],tokenize=True,add_generation_prompt=True,return_dict=True,processor_kwargs={'text_kwargs':{'padding':True},'return_tensors':'pt'})
        lengths=batch['input_features_mask'].sum(-1).long();expected=((lengths-1)//2+1-2)//2+1
        assert int((batch['input_ids'][0]==p.audio_token_id).sum())==int(expected.sum()),'Audio placeholders lost'
        return batch
    def infer(self,messages):
        inputs=self.prepare(messages).to(self.model.device).to(self.model.dtype);attempts=[]
        for cap in dict.fromkeys([self.cfg['max_tokens'],self.cfg['retry_tokens']]):
            torch.manual_seed(self.cfg['seed'])
            kw={'do_sample':False}
            if self.name=='qwen3_omni':kw.update(thinker_max_new_tokens=cap,return_audio=False,use_audio_in_video=False)
            else:kw['max_new_tokens']=cap
            with torch.inference_mode(), torch.autocast('cuda',dtype=torch.bfloat16):output=self.model.generate(**inputs,**kw)
            if isinstance(output,tuple):output=output[0]
            generated=output[:,inputs['input_ids'].shape[1]:];raw=self.processor.batch_decode(generated,skip_special_tokens=True,clean_up_tokenization_spaces=False)[0]
            config=self.model.thinker.generation_config if self.name=='qwen3_omni' else self.model.generation_config
            eos=config.eos_token_id;eos={eos} if isinstance(eos,int) else set(eos or [])
            if self.name=='qwen3_omni':eos.add(self.model.config.im_end_token_id)
            stopped=any(t in eos for t in generated[0].tolist());error=None if stopped and raw.strip() else ('length_truncated' if not stopped else 'empty_response')
            attempts.append({'max_tokens':cap,'error':error})
            if error!='length_truncated':break
        return dict(raw_text=raw,status='ok' if error is None else 'error',error=error,finish_reason='stop' if stopped else 'length',decode_max_tokens=cap,attempts=attempts,input_tokens=inputs['input_ids'].shape[1])
