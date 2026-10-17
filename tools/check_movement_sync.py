#!/usr/bin/env python3
"""Check captured tutorial steps for a camera-only intermediate map frame."""
from pathlib import Path
import json, hashlib
from PIL import Image

R=Path(__file__).resolve().parents[1]
results={}
for label in ('movement_tutorial','movement_sync_tutorial'):
    directory=R/'analysis/runtime'/label
    trace=json.loads((directory/'frame_trace.json').read_text())
    steps=[]
    for key in (7,6):
        begin=next(i for i,t in enumerate(trace) if t['keys']==[key] and trace[i-1]['keys']!=[key])
        events=trace[begin:begin+80]
        hashes=list(dict.fromkeys([trace[begin-1]['hash']]+[t['hash'] for t in events]))
        # Exclude message rows and HUD; compare the playfield pixel for pixel.
        crops=[Image.open(directory/'frames'/(h+'.png')).crop((0,24,240,144)).tobytes() for h in hashes]
        intermediate=[h for h,c in zip(hashes,crops) if c not in (crops[0],crops[-1])]
        steps.append({'direction':'right' if key==7 else 'left','intermediate_map_images':intermediate})
    latency=json.loads((directory/'input_latency.json').read_text())
    results[label]={'rom_sha256':latency['rom_sha256'],'steps':steps,'latency':latency['responses']}
assert any(s['intermediate_map_images'] for s in results['movement_tutorial']['steps']), 'Regression fixture must reproduce the reported defect'
assert all(not s['intermediate_map_images'] for s in results['movement_sync_tutorial']['steps'])
assert results['movement_sync_tutorial']['rom_sha256']==hashlib.sha256((R/'build/gba_zh_src/powder.gba').read_bytes()).hexdigest()
report={'result':'pass','samples':results,'limits':'Two deterministic tutorial steps in mGBA; real device feel still requires user play testing.'}
(R/'analysis/movement_sync_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Camera/map intermediate-frame regression passed for both directions')
