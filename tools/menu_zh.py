#!/usr/bin/env python3
"""Compact, translucent 10px action lists and 11px-ink parchment readers."""
from pathlib import Path
import re
p=Path(__file__).resolve().parents[1]/'build/zh_src/gfxengine.cpp'
s=p.read_text();root=p.parents[2]
cps=[int(n) for n in re.search(r'cps\[\]=\{([^}]+)',(p.parent/'zh_text.cpp').read_text())[1].split(',')]
codepoints=list(range(256))+cps
fontsets=[]
for size in (8,9,10,11):
 original=8 if size==8 else 10 if size<=10 else 12
 font=(root/f'assets/fonts/fusion-pixel-{original}px'/f'fusion-pixel-{original}px-monospaced-zh_hans.bdf').read_text()
 bitmaps={};wanted=set(codepoints)
 for block in font.split('STARTCHAR ')[1:]:
  lines=block.splitlines();cp=int(next(x for x in lines if x.startswith('ENCODING ')).split()[1])
  if cp not in wanted:continue
  w,h,xo,yo=map(int,next(x for x in lines if x.startswith('BBX ')).split()[1:]);rows=[0]*12;pos=lines.index('BITMAP')+1
  for y,row in enumerate(lines[pos:pos+h]):
   bits=int(row,16)
   for x in range(w):
    if bits & (1<<(len(row)*4-x-1)):
     xx=x+xo;yy=y+(7 if size==8 else 9 if size<=10 else 10)-h-yo-(1 if size in (9,11) else 0)
     if cp>=256 and size!=9: assert 0<=xx<size and 0<=yy<size,(cp,xx,yy)
     if 0<=xx<12 and 0<=yy<12:rows[yy]|=1<<xx
  if size==9:
   pts=[(x,y) for y,row in enumerate(rows) for x in range(12) if row&(1<<x)]
   if pts:
    dx=max(0,max(x for x,y in pts)-8);dy=max(0,max(y for x,y in pts)-8)
    if min(x for x,y in pts)<dx or min(y for x,y in pts)<dy:continue
    tight=[0]*12
    for x,y in pts:tight[y-dy]|=1<<(x-dx)
    rows=tight
  bitmaps[cp]=rows
 if size<=10:
  fallback=(root/'assets/fonts/fusion-pixel-8px/fusion-pixel-8px-monospaced-zh_hans.bdf').read_text()
  for block in fallback.split('STARTCHAR ')[1:]:
   l=block.splitlines();cp=int(next(x for x in l if x.startswith('ENCODING ')).split()[1])
   if cp not in wanted or cp in bitmaps:continue
   w,h,xo,yo=map(int,next(x for x in l if x.startswith('BBX ')).split()[1:]);pos=l.index('BITMAP')+1;rows=[0]*12
   for y,row in enumerate(l[pos:pos+h]):
    bits=int(row,16)
    for x in range(w):
     xx=x+xo+1;yy=y+7-h-yo+1
     if bits&(1<<(len(row)*4-x-1)) and 0<=xx<10 and 0<=yy<10:rows[yy]|=1<<xx
   bitmaps[cp]=rows
 assert set(cps)<=bitmaps.keys()
 fontsets.append('static const unsigned short zh_ink'+str(size)+'[][12]={\n'+',\n'.join('{'+','.join(map(str,bitmaps.get(c,[0]*12)))+'}' for c in codepoints)+'\n};\n')
(p.parent/'zh_ui_font.h').write_text(''.join(fontsets))
helper=(root/'tools/ui_zh_overlay.inc').read_text()
assert 'class ZHMenuPanel' not in s
s=s.replace('void\ngfx_displaylist(',helper+'\nvoid\ngfx_displaylist(',1)
needle='int &startoflist, int &endoflist)\n{'
s=s.replace(needle,needle+'\n    if(zh_menu_panel && zh_menu_panel->active){zh_menu_panel->draw(list,select,startoflist,endoflist);return;}',1)
s=s.replace('    // Display the menu.\n    gfx_displaylist','''    bool inventory_menu=glb_invmob && !menuactions && x==20 && y==3;
    ZHMenuPanel readable(menuactions!=0 || inventory_menu,inventory_menu?9:10,zh_grouped_action_menu);
    struct MenuScope {
        ZHMenuPanel *previous;
        MenuScope(ZHMenuPanel *p):previous(zh_menu_panel){zh_menu_panel=p;}
        ~MenuScope(){zh_menu_panel=previous;}
    } menu_scope(&readable);
    // Display the menu.
    gfx_displaylist''',1)
needle='    // Fast paging with left/right for cases where L/R'
s=s.replace(needle,'    if (readable.active) dy = dx > 0 ? readable.pageMove(select,num,1) : readable.pageMove(select,num,-1);\n'+needle,1)
# Pixel-width wrapping, while retaining blank paragraph lines and explicit single-line headings.
s=s.replace('zh_append(dst,src,glb_pager_width)','zh_pager_append(dst,src,glb_pager_width)').replace('zh_append(glb_pager[glb_pager_curline],src,glb_pager_width)','zh_pager_append(glb_pager[glb_pager_curline],src,glb_pager_width)')
s=s.replace('n>=glb_pager_width','n>=glb_pager_width')
# Return column sentinel when full, so the existing newline loop always progresses.
s=s.replace('zh_append(glb_pager[glb_pager_curline],text,glb_pager_width)','zh_pager_append(glb_pager[glb_pager_curline],text,glb_pager_width)')
# Reader owns VRAM temporarily; restore it before returning to the engine.
needle='gfx_pager_display(int y)\n{'
s=s.replace(needle,needle+'''\n    if(glb_gfxmode==0 && glb_pager) {
        if(zh_read_paper(glb_pager,glb_pager_curline+1,y)) {
            gfx_pager_reset();hamfake_clearKeyboardBuffer();return;
        }
    }\n''',1)
p.write_text(s)
# Keep labels, executed actions and remappable button IDs in the same order.
p=p.parent/'main.cpp';s=p.read_text()
groups=[
 ['CLIMB','SEARCH','LOOK','PICKUP','OPEN','CLOSE','MOVE','SAFEWALK','RUN','JUMP','MINIMAP'],
 ['FIRE','ZAP','BREATHE','USE','EAT','SWAP','RELEASE','COMMAND','INVENTORY'],
 ['WAIT','SLEEP','PRAY','FORGET','NAME','HISTORY','VERBLIST','WISH','OPTIONS']]
m=re.search(r'ACTION_NAMES\s+menu_generic\[\] =\s*\{.*?\};',s,re.S);assert m
clean=re.sub(r'//[^\n]*','',m[0]);old=re.findall(r'ACTION_([A-Z]+)',clean.split('{',1)[1])
ordered=[name for page in groups for name in page]+['NONE']
assert sorted(old)==sorted(ordered) and len(set(ordered))==len(ordered)
s=s[:m.start()]+'ACTION_NAMES menu_generic[] =\n{\n'+',\n'.join('    ACTION_'+name for name in ordered)+'\n};'+s[m.end():]
s=s.replace('ACTION_NAMES\nselectAssignment(', 'bool zh_grouped_action_menu=false;\nextern ACTION_NAMES menu_generic[];\n\nACTION_NAMES\nselectAssignment(',1)
s=s.replace('    select = gfx_selectmenu(30-12, 3, m, button, lastsel, true, true,', '    zh_grouped_action_menu=(menu==menu_generic);\n    select = gfx_selectmenu(30-12, 3, m, button, lastsel, true, true,',1)
s=re.sub(r'(glb_globalactionstrip\);\n)(    if \(select >= 0\))',r'\1    zh_grouped_action_menu=false;\n\2',s,count=1)
assert 'zh_grouped_action_menu=false;\n    if (select >= 0)' in s
p.write_text(s)
print('Installed compact 10px menu and 10px parchment reader')
