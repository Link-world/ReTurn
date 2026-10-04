import base64
import subprocess
from pathlib import Path
from functools import lru_cache

class Media:
    def __init__(self,cache):self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
    @lru_cache(maxsize=128)
    def silent(self,path):
        # Packaged clip names are unique; this directory belongs to one run contract.
        target=self.cache/(Path(path).stem+'.silent.mp4')
        if not target.exists():
            tmp=target.with_suffix('.partial.mp4')
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-threads','1','-i',path,'-map','0:v:0','-an','-vf',"scale=w='min(768,iw)':h='min(768,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",'-c:v','libx264','-threads','1','-preset','veryfast','-crf','20',str(tmp)],check=True,capture_output=True,timeout=180)
            tmp.replace(target)
        return str(target)
    @lru_cache(maxsize=128)
    def data(self,path,kind):
        if kind=='video':path=self.silent(path)
        mime='video/mp4' if kind=='video' else 'audio/wav'
        return 'data:'+mime+';base64,'+base64.b64encode(Path(path).read_bytes()).decode()
    def frames(self,path):
        import decord
        import numpy as np
        v=decord.VideoReader(self.silent(path),num_threads=1);fps=v.get_avg_fps();n=len(v)
        idx=np.unique(np.minimum(np.round(np.arange(0,n,max(1,fps/2))).astype(int),n-1))
        return v.get_batch(idx).asnumpy(),fps,idx,n
