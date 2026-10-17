#!/usr/bin/env python3
"""Place measured map-render hot paths in fast GBA RAM; retain turn/input rules."""
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]
S=Path(sys.argv[1]) if len(sys.argv)>1 else R/'build/zh_src'
attr='__attribute__((section(".iwram_movement"),long_call,noinline,optimize("O2")))'
for filename,names in [('map.cpp',['MAP::refresh']),('gfxengine.cpp',['gfx_settile','gfx_setoverlay','gfx_setmoblayer']),('port/gba/hamfake.cpp',['ham_SetMapTile'])]:
 p=S/filename;s=p.read_text()
 for name in names:
  pattern=r'\n(void)\n('+re.escape(name)+r'\()'
  s,n=re.subn(pattern,lambda m:'\n'+m[1]+' '+attr+'\n'+m[2],s,count=1)
  assert n==1,(filename,name)
 p.write_text(s)
print('Map renderer hot paths staged in IWRAM; no game rules or repeat timing changes')
# Most of the 1024 map cells are unchanged on a step. Avoid three function
# calls per unchanged cell; the setters keep their normal locking/upload path.
p=S/'map.cpp';s=p.read_text();s='extern unsigned short *glb_tilemap,*glb_mobmap,*glb_shadowmap;\n'+s
a=s.index('MAP::refresh(bool preserve_ray)');b=s.index('\nMOB *\nMAP::getGuiltyMob',a)
part=s[a:b]
for call,cache in [('gfx_settile(x, y, tile);','glb_tilemap'),('gfx_setmoblayer(x, y, mobtile);','glb_mobmap'),('gfx_setoverlay(x, y, tile);','glb_shadowmap')]:
 value='mobtile' if 'moblayer' in call else 'tile'
 assert call in part;part=part.replace(call,'if('+cache+'[y*32+x] != '+value+') '+call,1)
s=s[:a]+part+s[b:];p.write_text(s)

# Publish the world camera with its actor/map tiles, rather than at turn start.
# Look/target UI calls retain immediate camera updates.
p=S/'port/gba/hamfake.cpp';s=p.read_text()
s=s.replace('static void zh_check_present()',r'''static bool zh_defer_scroll=false;
static unsigned zh_scroll_pending=0;
static int zh_scroll_x[4],zh_scroll_y[4];
void ham_DeferWorldScroll(bool defer){zh_defer_scroll=defer;}
static void zh_commit_scroll(){
    for(int layer=1;layer<4;layer++){
        if(zh_scroll_pending&(1u<<(layer*2)))BG_OFFSET[layer].x=zh_scroll_x[layer];
        if(zh_scroll_pending&(2u<<(layer*2)))BG_OFFSET[layer].y=zh_scroll_y[layer];
    }
    zh_scroll_pending=0;
}
static void zh_check_present()''',1)
s=s.replace('delete [] zh_maps;zh_maps=0;', 'zh_commit_scroll();\n    delete [] zh_maps;zh_maps=0;',1)
for axis,bit in [('x',1),('y',2)]:
 old='    BG_OFFSET[layer].'+axis+' = scroll;'
 new=('    if(layer>0 && zh_defer_scroll){zh_scroll_'+axis+'[layer]=scroll;'
      'zh_scroll_pending|=('+str(bit)+'u<<(layer*2));return;}\n'
      '    zh_scroll_pending&=~('+str(bit)+'u<<(layer*2));\n'+old)
 assert old in s;s=s.replace(old,new,1)
p.write_text(s)
p=S/'gfxengine.cpp';s=p.read_text();s+='''
void ham_DeferWorldScroll(bool);
void gfx_scrollcenter_deferred(int x,int y){
    ham_DeferWorldScroll(true);
    gfx_scrollcenter(x,y);
    ham_DeferWorldScroll(false);
}
''';p.write_text(s)
for filename in ['main.cpp','action.cpp']:
 p=S/filename;s=p.read_text().replace('gfx_scrollcenter(', 'gfx_scrollcenter_deferred(')
 s='void gfx_scrollcenter_deferred(int,int);\n'+s;p.write_text(s)
print('World camera staged with map commit; UI panning remains immediate')
