#!/usr/bin/env python3
"""Optionally restore missing LLaVA clips from an authorized upstream dataset copy.

No network requests. Read only the named members from downloaded upstream archives,
or use their extracted directory tree. Existing destination files are never replaced.
"""
import argparse,json,shutil,subprocess,tarfile
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--source-root',type=Path);ap.add_argument('--archives-root',type=Path);ap.add_argument('--dest-root',type=Path);ap.add_argument('--list',action='store_true');a=ap.parse_args()
    rows=[r for r in json.loads((a.root/'data/media_manifest.json').read_text()) if r['source_dataset']=='LLaVA-Video-178K' and 'restore_recipe' in r]
    if a.list:
        for r in rows:print(r['media_id'],r['upstream_relative_path'],r['start_seconds'],r['end_seconds'])
        return
    if not a.source_root and not a.archives_root:ap.error('Supply --source-root or --archives-root after acquiring the upstream media under its original terms.')
    sources=a.source_root or a.archives_root/'selected_sources';dest=a.dest_root or a.root;sources.mkdir(parents=True,exist_ok=True)
    missing={r['upstream_relative_path'] for r in rows if not (sources/r['upstream_relative_path']).is_file()}
    if missing and a.archives_root:
        # Only copy explicitly listed regular files; never extract arbitrary tar paths or links.
        for archive in sorted(a.archives_root.rglob('*.tar.gz')):
            subset=archive.parent.name;targets={p for p in missing if p.split('/')[0]==subset}
            if not targets:continue
            with tarfile.open(archive,'r|gz') as tar:
                for member in tar:
                    if not member.isfile():continue
                    name=member.name.removeprefix('./');matching=[p for p in targets if name in [p,p.split('/',1)[1]]]
                    if not matching:continue
                    path=matching[0];target=sources/path;target.parent.mkdir(parents=True,exist_ok=True)
                    with tar.extractfile(member) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
                    missing.remove(path);targets.remove(path)
                    if not targets:break
    if missing:raise SystemExit('Missing exact upstream members: '+', '.join(sorted(missing)))
    restored=[]
    for r in rows:
        src=sources/r['upstream_relative_path'];recipe=r['restore_recipe'];start=str(r['start_seconds'])
        for kind in ['video','audio']:
            target=dest/r[kind]
            if target.exists():continue
            target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_name(target.stem+'.partial'+target.suffix)
            special=recipe['video_style']=='stage50_4fps_letterbox'
            cmd=['ffmpeg','-nostdin','-v','error','-n','-ss',start]
            if special:cmd+=['-t',str(recipe['video_requested_duration'])]
            cmd+=['-i',str(src)]
            if not special:cmd+=['-t',str(recipe['video_requested_duration'] if kind=='video' else recipe['audio_duration'])]
            if kind=='audio':cmd+=['-vn','-ar','16000','-ac','1','-c:a','pcm_s16le']
            else:
                if special:vf='fps=4,scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2'
                else:
                    side=recipe['video_max_side'];vf=f'scale={side}:{side}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2'
                cmd+=['-map','0:v:0','-an','-vf',vf,'-c:v','libx264','-preset','veryfast' if special else 'fast','-crf','20']
                if special:cmd+=['-pix_fmt','yuv420p','-movflags','+faststart']
                else:cmd+=['-threads','2']
                if recipe['video_max_side']==960:cmd+=['-movflags','+faststart']
            subprocess.run(cmd+[str(tmp)],check=True,capture_output=True,timeout=180);tmp.replace(target);restored.append(str(target.relative_to(dest)))
    print(json.dumps({'source_clips':len(rows),'restored_files':len(restored),'note':'Original source/windows and documented encoding. Container bytes can differ across FFmpeg builds; see restoration validation.'}))
if __name__=='__main__':main()
