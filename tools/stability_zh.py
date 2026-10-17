#!/usr/bin/env python3
"""VBlank commits and cached-map refreshes for the staged GBA renderer."""
from pathlib import Path
import re
R=Path(__file__).resolve().parents[1];S=R/'build/zh_src'
def patch_body(s,name,body):
 m=re.search(r'\n'+re.escape(name)+r'\([^;]*?\)\n\{',s);assert m,name
 rx=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]');level=1
 for t in rx.finditer(s,m.end()):
  if t[0]=='{':level+=1
  elif t[0]=='}':level-=1
  if not level:return s[:m.end()]+ '\n'+body+'\n'+s[t.start():]
 raise ValueError(name)
p=S/'port/gba/hamfake.cpp';s=p.read_text()
code=r'''
// CPU-side staging keeps bulk rebuilds off the visible maps and character data.
static u16 *zh_maps=0,*zh_tiles=0;
static unsigned char zh_dirty[512];
static int zh_map_depth=0,zh_tile_depth=0;
static bool zh_palette_pending=false;
volatile unsigned zh_present_total __attribute__((section(".ewram")))=0;
volatile unsigned zh_present_overruns __attribute__((section(".ewram")))=0;
volatile unsigned zh_overrun_work __attribute__((section(".ewram")))=0;
volatile unsigned zh_overrun_line __attribute__((section(".ewram")))=0;
volatile unsigned zh_world_rebuilds __attribute__((section(".ewram")))=0;
static void zh_check_present(){zh_present_total++;if(REG_VCOUNT<160)zh_present_overruns++;}
static void zh_vblank(){while(REG_VCOUNT>=160){}while(REG_VCOUNT<160){}}
static unsigned char *zh_mapbounds=0;
static u16 *zh_mapruns=0;static int zh_maprun_count=0;
static void zh_prepare_maps(){zh_maprun_count=0;if(!zh_maps)return;
    for(int layer=1;layer<4;layer++)for(int row=0;row<128;row++) {
        int at=((layer-1)*128+row)*2,lo=zh_mapbounds[at],hi=zh_mapbounds[at+1];if(lo>=hi)continue;
        int begin=row*32+lo,end=row*32+hi;
        u16 *prev=zh_maprun_count?zh_mapruns+(zh_maprun_count-1)*3:0;
        if(prev && prev[0]==layer && begin<=prev[1]+prev[2]+8)prev[2]=end-prev[1];
        else {u16 *out=zh_mapruns+zh_maprun_count++*3;out[0]=layer;out[1]=begin;out[2]=end-begin;}
    }
}
static void zh_commit_maps(){if(!zh_maps)return;
    for(int n=0;n<zh_maprun_count;n++) {
        u16 *r=zh_mapruns+n*3;int layer=r[0],offset=r[1];
        dmaCopy(zh_maps+(layer-1)*4096+offset,(void*)((u16*)SCREEN_BASE_BLOCK(ham_bg[layer].mi->blockid)+offset),r[2]*2);
    }
    delete [] zh_maps;zh_maps=0;zh_mapbounds=0;zh_mapruns=0;
}
void ham_BeginMapUpdate(){zh_map_depth++;if(zh_maps)return;zh_maps=new u16[3*4096+384+384*3];if(!zh_maps)return;
    zh_mapbounds=(unsigned char*)(zh_maps+3*4096);zh_mapruns=zh_maps+3*4096+384;
    for(int row=0;row<384;row++){zh_mapbounds[row*2]=255;zh_mapbounds[row*2+1]=0;}
    for(int layer=1;layer<4;layer++)dmaCopy((const void*)SCREEN_BASE_BLOCK(ham_bg[layer].mi->blockid),zh_maps+(layer-1)*4096,8192);
}
void ham_EndMapUpdate(){if(--zh_map_depth || zh_tiles || !zh_maps)return;zh_prepare_maps();zh_vblank();zh_commit_maps();zh_check_present();}
void ham_BeginTileUpdate(){zh_tile_depth++;if(zh_tiles)return;
    zh_tiles=new u16[512*32+256];if(!zh_tiles)return;
    memset(zh_dirty,0,sizeof(zh_dirty));zh_palette_pending=false;
}
void ham_EndTileUpdate(){if(--zh_tile_depth)return;
    if(!zh_tiles){if(!zh_map_depth && zh_maps){zh_prepare_maps();zh_vblank();zh_commit_maps();zh_check_present();}return;}
    zh_prepare_maps();zh_vblank();
    // Only upload changed runs, leaving room for the three map transfers.
    for(int i=0;i<512;i++)if(zh_dirty[i]){int end=i+1;while(end<512 && zh_dirty[end])end++;
        dmaCopy(zh_tiles+i*32,(void*)((u16*)CHAR_BASE_BLOCK(ham_bg[0].ti->blockid)+i*32),(end-i)*64);i=end-1;
    }
    if(zh_palette_pending)dmaCopy(zh_tiles+512*32,(void*)0x05000000,512);
    if(!zh_map_depth)zh_commit_maps();zh_check_present();delete [] zh_tiles;zh_tiles=0;
}
'''
s=s.replace('#define SRAMSIZE',code+'\n#define SRAMSIZE',1)
s=patch_body(s,'hamfake_awaitEvent','    updateOAM();\n    VBlankIntrWait();')
s=patch_body(s,'ham_ReloadTileGfx',r'''    if(destidx<0 || numtile<=0 || destidx+numtile>512)return;
    if(zh_tiles){memcpy(zh_tiles+destidx*32,data,numtile*64);memset(zh_dirty+destidx,1,numtile);return;}
    dmaCopy(data,(void*)((u16*)CHAR_BASE_BLOCK(tiledata->blockid)+destidx*32),numtile*64);''')
s=s.replace('u16\t\t*map = (u16 *) SCREEN_BASE_BLOCK(blockid);','u16\t\t*map = zh_maps && layer>0 ? zh_maps+(layer-1)*4096 : (u16 *) SCREEN_BASE_BLOCK(blockid);')
s=s.replace('    map[my*32 + mx] = tileidx;','''    if(zh_maps && layer>0 && map[my*32+mx]!=tileidx) {
        int index=map-zh_maps+my*32+mx,row=index/32,col=index%32;
        if(col<zh_mapbounds[row*2])zh_mapbounds[row*2]=col;
        if(col+1>zh_mapbounds[row*2+1])zh_mapbounds[row*2+1]=col+1;
    }
    map[my*32 + mx] = tileidx;''')
s=s.replace('ham_LoadBGPal(void *vpal, int bytes)\n{','ham_LoadBGPal(void *vpal, int bytes)\n{\n    if(zh_tiles){memcpy(zh_tiles+512*32,vpal,bytes);zh_palette_pending=true;return;}')
s='#include <string.h>\n'+s;p.write_text(s)
p=S/'gfxengine.cpp';s=p.read_text()
# A render commit may already have delivered the current frame interrupt.
# Consume it before waiting again; raw button-release waits still sleep normally.
s=s.replace('    hamfake_awaitEvent();\n    // The event could be a new frame...',
            '    if (!glb_newframe) hamfake_awaitEvent();\n    // The event could be a new frame...',1)
s='''void ham_BeginMapUpdate();void ham_EndMapUpdate();
void ham_BeginTileUpdate();void ham_EndTileUpdate();
struct ZHMapUpdate{ZHMapUpdate(){ham_BeginMapUpdate();}~ZHMapUpdate(){ham_EndMapUpdate();}};
struct ZHTileUpdate{ZHTileUpdate(){ham_BeginTileUpdate();}~ZHTileUpdate(){ham_EndTileUpdate();}};
'''+s
# The refresh path rewrites all three 64x64 maps; every staged element is assigned.
a=s.index('\ngfx_refreshtiles()');b=s.index('\nvoid\ngfx_settile(',a)
part=s[a:b].replace('if (glb_gfxmode)\n\treturn;','if (glb_gfxmode)\n\treturn;\n    ZHMapUpdate atomic_refresh;',1)
s=s[:a]+part+s[b:]
for name in ['gfx_switchfonts','gfx_switchtilesets']:
 a=s.index('\n'+name+'(');b=s.index('\n}\n',a)
 part=s[a:b].replace('if (glb_gfxmode)\n\treturn;','if (glb_gfxmode)\n\treturn;\n    ZHTileUpdate atomic_tiles;',1)
 s=s[:a]+part+s[b:]
# Colored glyph slots are virtual cache keys, not alphabet character codes.
s=s.replace('u8\t*glb_colourchardata[MAX_COLOUR_CHAR];','u8\t*glb_colourchardata[MAX_COLOUR_CHAR];\nu16 zh_colour_code[MAX_COLOUR_CHAR];\nCOLOUR_NAMES zh_colour_name[MAX_COLOUR_CHAR];')
s=s.replace('charnum = virtualtile - COLOURED_SYMBOLS;','charnum = virtualtile - COLOURED_SYMBOLS;\n    zh_colour_code[charnum]=c;zh_colour_name[charnum]=colour;')
helper=r'''
static void zh_reload_colours(){for(int n=0;n<MAX_COLOUR_CHAR;n++) {
    int idx=glb_charidx[COLOURED_SYMBOLS+n];if(idx==INVALID_TILEIDX || !glb_colourchardata[n])continue;
    const u8 *src=&glb_tilesets[glb_tileset].alphabet[glb_currentfont][gfx_getchartile(zh_colour_code[n])*64];
    u8 *dst=glb_colourchardata[n];
    for(int i=0;i<64;i++)dst[i]=!src[i]?0:src[i]==glb_stdcolor[COLOUR_BLACK]?glb_stdcolor[COLOUR_BLACK]:glb_stdcolor[zh_colour_name[n]];
    ham_ReloadTileGfx(glb_bg1tiles,(u16*)dst,idx,1);
}}
'''
s=s.replace('void\ngfx_switchfonts(',helper+'\nvoid\ngfx_switchfonts(',1)
for name in ['gfx_switchfonts','gfx_switchtilesets']:
 a=s.index('\n'+name+'(');b=s.index('\n}\n',a)
 part=s[a:b].replace('for (c = 0; c < ZH_GLYPH_COUNT; c++)\n    {','for (c = 0; c < ZH_GLYPH_COUNT; c++)\n    {\n        if(c>=COLOURED_SYMBOLS && c<COLOURED_SYMBOLS+MAX_COLOUR_CHAR)continue;')
 part+='\n    zh_reload_colours();\n';s=s[:a]+part+s[b:]
p.write_text(s)
print('Staged VBlank, DMA, atomic map/font updates and colored-cache preservation')

# A whole map redraw keeps the old room visible until tile and map data agree.
p=S/'map.cpp';s=p.read_text();s='void ham_BeginMapUpdate();void ham_EndMapUpdate();void ham_BeginTileUpdate();void ham_EndTileUpdate();\nextern int glb_gfxmode;\nstruct ZHSceneUpdate{bool active;ZHSceneUpdate():active(glb_gfxmode==0){if(active){ham_BeginTileUpdate();ham_BeginMapUpdate();}}~ZHSceneUpdate(){if(active){ham_EndMapUpdate();ham_EndTileUpdate();}}};\n'+s
s=s.replace('MAP::refresh(bool preserve_ray)\n{','MAP::refresh(bool preserve_ray)\n{\n    ZHSceneUpdate atomic_scene;');p.write_text(s)

p=S/'main.cpp';s=p.read_text();s='extern volatile unsigned zh_world_rebuilds;\n'+s
s=s.replace('rebuild_all()\n{','rebuild_all()\n{\n    zh_world_rebuilds++;');p.write_text(s)
