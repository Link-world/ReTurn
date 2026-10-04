"""Fix HF's conversation-count/audio-count check, preserving official token expansion."""
from transformers import AudioFlamingo3Processor
from transformers.processing_utils import ProcessorMixin

class MultiTurnAudioProcessor(AudioFlamingo3Processor):
    def validate_inputs(self,audio=None,text=None,**kwargs):
        ProcessorMixin.validate_inputs(self,audio=audio,text=text,**kwargs)
        if audio is not None and text is not None:
            texts=[text] if isinstance(text,str) else text
            placeholders=sum(t.count(self.audio_token) for t in texts)
            if placeholders!=len(audio):
                raise ValueError(f'Expected one sound placeholder per audio: {placeholders} placeholders, {len(audio)} audios')

def load_processor(path):
    # Construct from the official processor components; no installed package mutation.
    from transformers import AutoProcessor
    p=AutoProcessor.from_pretrained(path)
    return MultiTurnAudioProcessor(feature_extractor=p.feature_extractor,tokenizer=p.tokenizer,
        chat_template=p.chat_template,audio_token=p.audio_token,
        default_transcription_prompt=p.default_transcription_prompt,max_audio_len=p.max_audio_len)
