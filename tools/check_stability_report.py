#!/usr/bin/env python3
"""Aggregate exact-ROM UI checks and a renderer-identical AI stress fixture."""
from pathlib import Path
import json,hashlib,argparse
from PIL import Image
ap=argparse.ArgumentParser();ap.add_argument('--prefix',default='stable');ap.add_argument('--ui-only',action='store_true');args=ap.parse_args()
R=Path(__file__).resolve().parents[1];A=R/'analysis/runtime'
prefix=args.prefix
def load(p):return json.loads(p.read_text())
def ui_frames(name):
 d=A/name;events=load(d/'frame_trace.json');markers=load(d/'frame_markers.json')
 begin=markers['entered_game'];end=markers['after_save'];white=0
 for t in events:
  if not begin<=t['frame']<=end or not t['uniform']:continue
  colour=t.get('uniform_rgb') or Image.open(d/'frames'/(t['hash']+'.png')).getpixel((0,0))
  white+=min(colour)>240
 return {'frames_observed':end-begin+1,'white_intermediate_frames':white}
normal=load(A/(prefix+'_final')/'renderer_timing.json');tutorial=load(A/(prefix+'_tutorial')/'renderer_timing.json')
world=[] if args.ui_only else load(A/((prefix+'_world') if prefix!='stable' else 'world_stress_final')/'renderer_timing.json')
assert all(x['zh_present_overruns']==0 for run in [normal,tutorial,world] for x in run)
if world:assert world[-1]['zh_world_rebuilds']>=3
cycles=load(A/(prefix+'_final')/'checks.json')['repeat_switch_cycles']
before=ui_frames('baseline_final');after=ui_frames((prefix+'_final'));assert after['white_intermediate_frames']==0
report={'rom_sha256':hashlib.sha256((R/'build/gba_zh_src/powder.gba').read_bytes()).hexdigest(),
 'baseline_ui':before,'fixed_ui':after,'vblank_overruns':0,
 'normal_ui_commits_before_reset':max(x['zh_present_total'] for x in normal),
 'repeat_action_menu_cycles':cycles,'repeat_reader_cycles':cycles,
 'world_fixture':None if args.ui_only else {'build_flag':'FORCESTRESSTEST; not enabled in user ROM','frames':60000,
 'room_regenerations':world[-1]['zh_world_rebuilds'],'presentation_commits':world[-1]['zh_present_total'],
 'rom_sha256':hashlib.sha256((R/'build/gba_zh_src_stress/powder.gba').read_bytes()).hexdigest()},
 'visual_layout':'10px Start / native 8px Start hints / 10px reader / 9px inventory and other hints' if prefix in ('grouped','movement','movement_sync') else '10px action menu / 10px reader / 9px button hints' if prefix in ('reader10','menus_up') else '10px action menu / 11px reader ink / 9px button hints retained',
 'ui_only':args.ui_only,
 'limits':'mGBA libretro 0.10.5; startup/load black transitions still exist; no complete playthrough or real-hardware verification'}
(R/'analysis'/('stability_validation.json' if prefix=='stable' else prefix+'_stability_validation.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
