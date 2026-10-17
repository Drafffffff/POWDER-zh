#!/usr/bin/env python3
"""Package the verified Chinese build and round-trip a BPS patch."""
from pathlib import Path
import importlib.util,json,hashlib,shutil,argparse
ap=argparse.ArgumentParser();ap.add_argument('--prefix',default='stable');args=ap.parse_args();prefix=args.prefix
R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rom_text',R.parent/'tools/rom_text.py')
rom_text=importlib.util.module_from_spec(spec);spec.loader.exec_module(rom_text)
source=(R/'original/powder118.gba').read_bytes()
target=(R/'build/gba_zh_src/powder.gba').read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
checks=json.loads((R/'analysis/runtime'/(prefix+'_final')/'checks.json').read_text())
assert checks['rom_sha256']==sha(target),'Run runtime checks for this exact ROM first'
assert sha(source)=='20bf244560265e8215ea9df2d23c3c85a93bb49f1a91010a230d0d125cc3b654'
assert target[0xbd]==(-sum(target[0xa0:0xbd])-0x19)&255
stability=json.loads((R/'analysis'/('stability_validation.json' if prefix=='stable' else prefix+'_stability_validation.json')).read_text())
assert stability['rom_sha256']==sha(target)
performance=None
if prefix=='smooth':
 performance=json.loads((R/'analysis/performance_validation.json').read_text())
 assert performance['rom_sha256']==sha(target)
out=R/'output';out.mkdir(exist_ok=True)
name='powder118_zh_'+('smooth' if prefix=='smooth' else prefix)
(out/(name+'.gba')).write_bytes(target)
patch=rom_text.make_bps(source,target);rom_text.verify_bps(source,patch,target)
(out/(name+'.bps')).write_bytes(patch)
shutil.copy2(R/'analysis/runtime'/(prefix+'_final')/'command_menu_3x.png',out/(name+'.png'))
shutil.copy2(R/'analysis/runtime'/(prefix+'_tutorial')/'tutorial_signpost_3x.png',out/(name+'_signpost.png'))
manifest={'stability':stability,'rom':name+'.gba','rom_bytes':len(target),'rom_sha256':sha(target),
 'original_sha256':sha(source),'bps_sha256':sha(patch),'bps_roundtrip':'pass',
 'runtime':checks,'translation_validation':json.loads((R/'analysis/zh_validation.json').read_text()),
 'menu':{'glyph':'Fusion Pixel 10px, transparent background, dark outline; 9px button hints','rows_per_page':9 if prefix in ('compact_menus','reader10','menus_up','grouped','movement','movement_sync') else 7,'line_spacing_px':12 if prefix in ('compact_menus','reader10','menus_up','grouped','movement','movement_sync') else 15,
 'navigation':'D-pad up/down: select; left/right: page; A: execute; B: return'},
 'reader':{'glyph':'11px native ink, with blank BDF border removed; no resampling','button_hints_px':9,'visible_lines':8,'line_spacing_px':13},
 'scope':'Chinese test build; action-menu layout improved; no complete-game playthrough or old-save compatibility certification'}
if prefix in ('inventory9','inventory_compact','compact_menus','reader10','menus_up','grouped','movement','movement_sync'):
 manifest['inventory_menu']={'glyph_px':9,'previous_glyph_px':8,'rows_per_page':11 if prefix!='inventory9' else 8,'line_spacing_px':10 if prefix!='inventory9' else 13,'navigation':'up/down select; left/right page; A execute; B return'}
 assert checks.get('inventory_action_checks'), 'Run inventory action checks first'
 shutil.copy2(R/'analysis/runtime'/(prefix+'_final')/'item_action_menu_3x.png',out/(name+'_inventory.png'))
if prefix in ('compact_menus','reader10','menus_up','grouped','movement','movement_sync'):
 latency=json.loads((R/'analysis/runtime'/(prefix+'_final')/'input_latency.json').read_text())
 assert latency['rom_sha256']==sha(target)
 manifest['input_latency']=latency
if prefix in ('reader10','menus_up','grouped','movement','movement_sync'):
 manifest['reader']={'glyph':'Fusion Pixel 10px native dot matrix','glyph_px':10,'button_hints_px':9,'visible_lines':9,'line_spacing_px':12}
if prefix=='menus_up':manifest['menu']['panel_top_px']=8;manifest['menu']['first_text_top_px']=16
if prefix in ('grouped','movement','movement_sync'):
 assert checks.get('grouped_actions_reachable')==29
 manifest['menu'].update({'rows_per_page':11,'line_spacing_px':11,'first_text_top_px':9,'page_number_top_px':9,'button_hints_px':8,'category_pages':[{'name':'探索移动','actions':11},{'name':'战斗与物品','actions':9},{'name':'休息与系统','actions':9}]})
 manifest['menu']['glyph']='Fusion Pixel 10px; native 8px footer'
 for number in (2,3):shutil.copy2(R/'analysis/runtime'/(prefix+'_final')/('group_page_'+str(number)+'_3x.png'),out/(name+'_page'+str(number)+'.png'))
if prefix in ('movement','movement_sync'):
 performance=json.loads((R/'analysis'/('movement_performance.json' if prefix=='movement' else 'movement_sync_performance.json')).read_text())
 assert performance['rom_sha256']==sha(target)
if prefix=='movement_sync':
 manifest['movement_sync']=json.loads((R/'analysis/movement_sync_validation.json').read_text())
if performance:manifest['performance']=performance
(out/(name+'.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'rom':str(out/(name+'.gba')),'sha256':sha(target),'bps_roundtrip':'pass'},ensure_ascii=False))
