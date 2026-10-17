#!/usr/bin/env python3
"""Apply the Chinese engine adaptation only to the staged build source."""
from pathlib import Path
import re
R=Path(__file__).resolve().parents[1]; S=R/'build/zh_src'
def function(s,name,body):
 # Locate declaration with a newline before its name, and replace its balanced body.
 m=re.search(r'\n'+re.escape(name)+r'\([^;]*?\)\n\{',s); assert m,name
 start=m.end()-1; n=1;i=start+1
 # C token-aware brace balance.
 rx=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
 for t in rx.finditer(s,i):
  if t[0]=='{':n+=1
  if t[0]=='}':n-=1
  if not n:return s[:start]+'{\n'+body+'\n}'+s[t.end():]
 raise ValueError(name)
def inject(s,name,code):
 m=re.search(r'\n'+re.escape(name)+r'\([^;]*?\)\n\{',s);assert m,name
 return s[:m.end()]+'\n'+code+'\n'+s[m.end():]
p=S/'gfxengine.cpp';s=p.read_text();s='#include "zh_text.h"\n'+s
s=s.replace('glb_charidx[256]','glb_charidx[ZH_GLYPH_COUNT]')
s=re.sub(r'u8(\s+\*glb_charmap)',r'u16\1',s).replace('new u8[32*24]','new u16[32*24]').replace('0xff, 32*24','0xff, 32*24*sizeof(u16)').replace('sizeof(u16) * 256','sizeof(glb_charidx)')
for name in ['gfx_getchartile','gfx_printcharraw','gfx_printcolourcharraw','gfx_printchar','gfx_printcolourchar']:
 s=re.sub(r'('+name+r'\(int x, int y, )char c',r'\1u16 c',s) if name!='gfx_getchartile' else s.replace('gfx_getchartile(char c)','gfx_getchartile(u16 c)')
s=s.replace('gfx_lockColourCharTile(u8 c, COLOUR_NAMES colour, u8 *result)','gfx_lockColourCharTile(u16 c, COLOUR_NAMES colour, u16 *result)').replace('gfx_lockCharTile(u8 c, u8 *result)','gfx_lockCharTile(u16 c, u16 *result)').replace('gfx_unlockCharTile(u8 c)','gfx_unlockCharTile(u16 c)').replace('(u8 *) &c','&c')
s=s.replace('*result = 0xff','*result = 0xffff').replace('if (c == 0xff)','if (c == 0xffff)').replace('glb_charmap[y*32+x] != 0xff','glb_charmap[y*32+x] != 0xffff')
s=inject(s,'gfx_getchartile','    if(c >= 256) return 120+c-256;')
for name in ['gfx_printchar','gfx_printcolourchar','gfx_printcharraw','gfx_printcolourcharraw']:
 s=inject(s,name,'    if(c >= 0xff00) c &= 255;\n    if(c >= ZH_GLYPH_COUNT) c = \'?\';')
s=s.replace('if (*text == c)','if ((unsigned char)*text == c)')
s=s.replace('gfx_printchar(x++, y, *text++);','gfx_printchar(x++, y, zh_next(text));')
s=re.sub(r'gfx_printchar\((x|sx), (y|sy), \*text\);\s*text\+\+;',r'gfx_printchar(\1, \2, zh_next(text));',s)
s=s.replace('width = strlen(prompt);','width = zh_len(prompt);')
s=s.replace('x+strlen(entry)','x+zh_len(entry)').replace('c < 255','c < ZH_GLYPH_COUNT')
s=s.replace('new char[glb_pager_width+2]','new char[glb_pager_width*3+4]')
s=function(s,'gfx_pager_addtext', '''    if (!glb_pager) { glb_pager_curline=-1; glb_pager_size=0; gfx_pager_newline(); }
    const char *src=text;
    while (*src) {
        char *dst=glb_pager[glb_pager_curline];
        int n=zh_append(dst,src,glb_pager_width);
        if(*src && n>=glb_pager_width) { gfx_pager_newline(); while(*src==' ')src++; }
    }''') # first overload BUF? first gfx_pager_addtext(BUF buf) before const => replaces wrong! below correct
# Fix overload: replacing BUF version above is invalid. Rebuild targeted selection below handled via function named pattern.
s=s.replace('gfx_pager_addtext(BUF buf)\n{\n    if (!glb_pager)', 'gfx_pager_addtext(BUF buf)\n{\n    const char *text=buf.buffer();\n    if (!glb_pager)')
# Replace const char* overload explicitly by temporarily renaming.
s=s.replace('gfx_pager_addtext(const char *text)','gfx_pager_addtext_utf8(const char *text)')
s=function(s,'gfx_pager_addtext_utf8','''    if (!glb_pager) { glb_pager_curline=-1; glb_pager_size=0; gfx_pager_newline(); }
    const char *src=text;
    while(*src){ int n=zh_append(glb_pager[glb_pager_curline],src,glb_pager_width);
      if(*src && n>=glb_pager_width){gfx_pager_newline();while(*src==' ')src++;}}
''').replace('gfx_pager_addtext_utf8','gfx_pager_addtext')
s=function(s,'gfx_pager_addsingleline','''    if(!glb_pager){glb_pager_curline=-1;glb_pager_size=0;gfx_pager_newline();}
    if(*glb_pager[glb_pager_curline])gfx_pager_newline();
    zh_append(glb_pager[glb_pager_curline],text,glb_pager_width);
    gfx_pager_newline();''')
s=s.replace('curtext -= 30;','const char *prev=text; while(zh_advance(prev,30)<curtext)prev=zh_advance(prev,30); curtext=prev;').replace('strlen(curtext) >= 30 * (18 - 4)','zh_len(curtext) >= 30 * (18 - 4)').replace('curtext += 30;','curtext=zh_advance(curtext,30);')
p.write_text(s)
p=S/'gfxengine.h';s=p.read_text();s=re.sub(r'(gfx_print\w*char\w*\(int x, int y, )char c',r'\1u16 c',s);p.write_text(s)
p=S/'msg.cpp';s='#include "zh_text.h"\n'+p.read_text();s=s.replace('new char[SCREEN_WIDTH+1]','new char[SCREEN_WIDTH*3+4]')
s=function(s,'msg_write','''    glbViewingOld=false;
    const char *src=str;
    while(*src){
        char *dst=glbMsg[glbCurLine]; int limit=SCREEN_WIDTH-(glbCurLine==PAGE_SIZE-1);
        int n=zh_append(dst,src,limit);
        if(!*src){msg_refresh();return;}
        if(n>=limit){
            if(glbCurLine==PAGE_SIZE-1){int bytes=strlen(dst);dst[bytes]=SYMBOL_NEXT;dst[bytes+1]=0;msg_refresh();if(wait)msg_awaitaccept();msg_clear();}
            else glbCurLine++;
            while(*src==' ')src++;
        }
    }
    msg_refresh();''')
# Announcement wrapping by codepoint avoids rewinding into a UTF-8 sequence.
a=s.index('    cur = msg;',s.index('msg_announce(')); b=s.index('    // Await confirmation',a)
s=s[:a]+'''    cur=msg;
    while(*cur && y<19){gfx_printchar(x++,y,zh_next(cur));if(x>=SCREEN_WIDTH){x=0;y++;}}

'''+s[b:];p.write_text(s)
p=S/'grammar.cpp';s='#include "zh_text.h"\n'+p.read_text()
# Chinese nouns have neither articles nor plural suffixes.
s=s.replace('gram_makeplural(BUF phrase)\n{','gram_makeplural(BUF phrase)\n{\n    if(zh_has(phrase.buffer())) return phrase;')
s=inject(s,'gram_isnameplural','    if(zh_has(name))return false;')
s=inject(s,'gram_isplural','    if(zh_has(noun))return false;')
s=inject(s,'gram_getarticle','    if(zh_has(noun))return "";')
s=s.replace('gram_createcount(BUF basename, int count, bool article)\n{','gram_createcount(BUF basename, int count, bool article)\n{\n    if(zh_has(basename.buffer())){if(count==1)return basename;BUF b;b.sprintf("%d个%s",count,basename.buffer());return b;}')
s=s.replace('gram_makepossessive(BUF str)\n{','gram_makepossessive(BUF str)\n{\n    {BUF b=str;b.strcat("的");return b;}')
s=inject(s,'gram_conjugate','    if(zh_has(verb)){BUF b;b.strcpy(verb);return b;}')
s=s.replace('gram_capitalize(BUF buf)\n{','gram_capitalize(BUF buf)\n{\n    if(zh_has(buf.buffer()))return buf;')
# Only pronoun data tables change; comparisons in the English fallback stay intact.
pron=['我','你','他','她','它','我们','你们','他们','他们','他们']
for name,suffix in [('pronoun',''),('possessive','的'),('ownership','的'),('reflexive','自己'),('accusative','')]:
 s=re.sub(r'(glb_'+name+r'\[NUM_VERBS\]\s*=\s*)\{[^}]+\}',lambda m:m[1]+'{'+','.join('"'+x+suffix+'"' for x in pron)+'}',s)
p.write_text(s)
p=S/'creature.cpp';s=p.read_text().replace('buf.reference("you")','buf.reference("你")').replace('buf.strcpy("the ")','buf.strcpy("")').replace('buf.reference("the ")','buf.reference("")');p.write_text(s)
p=S/'item.cpp';s=p.read_text().replace('buf.strcpy("the ")','buf.strcpy("")');p.write_text(s)
print('Engine UTF-8, cache, wrap and grammar patched')

p=S/'victory.cpp';s=p.read_text();s=re.sub(r'\(\w+ == 1\) \? "" : "s"','""',s);p.write_text(s)

# GBA NO_HAM's original cursor hooks are stubs. Use a 16x16, 256-color OBJ.
p=S/'gfxengine.cpp';s=p.read_text()
s=function(s,'hamfake_movesprite','''    volatile u16 *o=(volatile u16*)0x07000000;
    o[spriteno*4]=(o[spriteno*4]&0xff00)|(y&255);
    o[spriteno*4+1]=0x4000|(x&511);''')
s=function(s,'hamfake_enablesprite','''    volatile u16 *o=(volatile u16*)0x07000000;
    o[spriteno*4]=(o[spriteno*4]&255)|0x2000|(enabled?0:0x0200);
    o[spriteno*4+1]|=0x4000; o[spriteno*4+2]=spriteno*8;''')
s=function(s,'hamfake_ReloadSpriteGfx','''    volatile u16 *dst=(volatile u16*)0x06010000;
    dst+=tileno*32;for(int i=0;i<numtile*32;i++)dst[i]=data[i];''')
s=function(s,'hamfake_LoadSpritePal','''    volatile u16 *dst=(volatile u16*)0x05000200;const u16 *src=(const u16*)data;
    for(int i=0;i<bytes/2;i++)dst[i]=src[i];''')
p.write_text(s)
p=S/'port/gba/hamfake.cpp';s=p.read_text();s=s.replace('BG3_ON;', 'BG3_ON | OBJ_ON | OBJ_1D_MAP;')
s=s.replace('ham_vramtop = 0;','ham_vramtop = 0;')
# Init OAM disabled because power-on values can display unintended sprites.
s=s.replace('ham_SetBgMode(u8 mode)\n{', 'ham_SetBgMode(u8 mode)\n{\n    if(mode==0){volatile u16 *o=(volatile u16*)0x07000000;for(int i=0;i<128;i++)o[i*4]=0x0200;}')
p.write_text(s)
