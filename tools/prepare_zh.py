#!/usr/bin/env python3
"""Stage source, apply reviewed catalogs, and generate a UTF-8 8px font build."""
import json,re,pathlib,shutil,subprocess,collections
R=pathlib.Path(__file__).resolve().parents[1]; S=R/'build/zh_src'
if S.exists(): shutil.rmtree(S)
shutil.copytree(R/'source',S)
D=json.loads((R/'translations/data_zh.json').read_text()); U=json.loads((R/'translations/ui_zh.json').read_text()); M=json.loads((R/'translations/messages_zh.json').read_text()); H=json.loads((R/'translations/help_zh.json').read_text())
for d in [D,U,M,H]:
 if not all(isinstance(v,str) for v in d.values()): raise ValueError('Catalog must be flat')
E=json.loads((R/'translations/extra_zh.json').read_text()); ALL={**D,**M,**U,**E}; stats=collections.Counter(); missing=[]
# Tokenize comments and chars first so quoted comments and includes are not modified.
TOKEN=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*"')
def decode(s):
 return bytes(s[1:-1],'utf-8').decode('unicode_escape')
def quote(s): return json.dumps(s,ensure_ascii=False)
def localize(text,mapping,file,normalize=False):
 toks=[m for m in TOKEN.finditer(text) if m[0].startswith(chr(34))]; out=[]; at=0; i=0
 while i<len(toks):
  m=toks[i]; start,end=m.span(); i+=1
  if not m[0].startswith('"') or re.search(r'#\s*include\s*$',text[max(0,start-30):start]): continue
  if re.search(r'encyc_(?:viewentry|hasentry|getentry|pageentry)\(\s*$',text[max(0,start-80):start]):continue
  val=decode(m[0]); j=i
  while j<len(toks) and toks[j][0].startswith('"') and not re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',text[end:toks[j].start()]).strip():
   val+=decode(toks[j][0]); end=toks[j].end(); j+=1
  key=' '.join(val.split()) if normalize else val
  if key not in mapping:
   # Fall back to individual fragments if a full adjacent group is not catalogued.
   if j>i:
    if len(val)>3 and re.search('[A-Za-z]{3}',val):missing.append({'file':file,'text':val,'adjacent':True})
    continue
   if len(val)>3 and re.search('[A-Za-z]{3}',val): missing.append({'file':file,'text':val})
   continue
  i=j; out.append(text[at:start]); out.append(quote(mapping[key])); at=end; stats[file]+=1
 out.append(text[at:]); return ''.join(out)
# Keep reference data and identifiers intact; replace only quoted field values.
p=S/'source.txt'
def field(m):
 v=decode(m[0]); stats['source.txt']+=v in D; return quote(D[v]) if v in D else m[0]
p.write_text(re.sub(r'"(?:\\.|[^"\\])*"',field,p.read_text()))
subprocess.run([str(R/'build/host/enummaker'),'source.txt'],cwd=S,check=True,stdout=subprocess.DEVNULL)
for p in S.glob('*.cpp'):
 if p.name in ['encyclopedia.cpp','glbdef.cpp','grammar.cpp','license.cpp','credits.cpp']: continue
 p.write_text(localize(p.read_text(),{**ALL,**H} if p.name=='encyclopedia.cpp' else ALL,p.name,normalize=p.name=='encyclopedia.cpp'))
# The historical encyclopedia2c misreads titles without a dash separator.
books=collections.OrderedDict(); cur=None
for line in (R/'source/encyclopedia.txt').read_text().splitlines():
 if line.startswith('#'):continue
 m=re.match(r'^(\w+)::(\w+)(?:\s+(?:-\s+)?(.*))?$',line)
 if m:
  book,key,title=m.groups(); cur={'id':book+'_'+key,'name':(title or '').strip(),'paras':[],'pending':[]}; books.setdefault(book,[]).append(cur)
 elif cur is not None:
  if line.strip():cur['pending'].append(line.strip())
  elif cur['pending']:cur['paras'].append(' '.join(' '.join(cur['pending']).split()));cur['pending']=[]
 # At a new entry the previous pending paragraph has been flushed by the separating blank.
assert all(not e['pending'] for es in books.values() for e in es)
cpp=['#include "encyclopedia.h"','#include "glbdef.h"']; total=0; missed=[]
for book,es in books.items():
 for e in es:
  lines=[]
  for para in e['paras']:
   if para not in H:missed.append(para)
   lines += [H.get(para,para),'']; total+=1
  if lines:lines.pop()
  id=e['id'];cpp.append('const char *glb_encyclopedia_entry_'+id+'_lines[]={'+','.join(quote(x) for x in lines)+'};')
  cpp.append('const encyclopedia_entry glb_encyclopedia_entry_'+id+'={'+id+','+quote(ALL.get(e['name'],e['name']))+','+str(len(lines))+',glb_encyclopedia_entry_'+id+'_lines};')
 cpp.append('const encyclopedia_entry *glb_encyclopedia_book_'+book+'_entrylist[]={'+','.join('&glb_encyclopedia_entry_'+e['id'] for e in es)+'};')
 cpp.append('const encyclopedia_book glb_encyclopedia_book_'+book+'={'+quote(book)+','+str(len(es))+',glb_encyclopedia_book_'+book+'_entrylist};')
cpp.append('const encyclopedia_book *glb_encyclopedia[NUM_ENCYCLOPEDIA_BOOKS]={'+','.join('&glb_encyclopedia_book_'+b for b in books)+'};')
(S/'encyclopedia.cpp').write_text('\n'.join(cpp)+'\n');stats['encyclopedia paragraphs']=total-len(missed)
if missed:raise ValueError('Missing encyclopedia paragraphs: '+repr(missed))

p=S/'gfx/all_bitmaps.cpp';p.write_text(localize(p.read_text(),ALL,'gfx/all_bitmaps.cpp'))
# Compatibility with the current standard ARM/newlib ABI. GBA has no file-based BMP loader.
p=S/'port/gba/mygba.h';p.write_text(p.read_text().replace('#if 1\n','#if 0\n'))
p=S/'victory.cpp';p.write_text(p.read_text().replace('stricmp(', 'strcasecmp('))
p=S/'port/gba/hamfake.cpp';p.write_text(p.read_text().replace('REG_DISPCNT = MODE_3;', 'REG_DISPCNT = MODE_3 | BG2_ON;').replace('ham_AllocateVramBlock(vramsize, 0x2000)', 'ham_AllocateVramBlock(vramsize, 0x4000)'))
p=S/'bmp.cpp';p.write_text(p.read_text().replace('hamfake_fopen(name, "rb")','fopen(name, "rb")'))
# Collect all characters from translated literals plus the engine's Chinese grammar vocabulary.
extra='我你他她它我们你们他们的自己个第无行动菜单上下选择执行返回'
chars=sorted({c for d in [D,U,M,H,E] for v in d.values() for c in v if ord(c)>255}|set(extra),key=ord)
# BDF native bitmap, no antialiasing. Native ink is moved up only when the blank top allows it.
font=(R/'assets/fonts/fusion-pixel-8px/fusion-pixel-8px-monospaced-zh_hans.bdf').read_text(); glyphs={}
for block in font.split('STARTCHAR ')[1:]:
 lines=block.splitlines(); cp=int(next(x for x in lines if x.startswith('ENCODING ')).split()[1]);
 if chr(cp) not in chars: continue
 w,h,xo,yo=map(int,next(x for x in lines if x.startswith('BBX ')).split()[1:]); top=7-h-yo; mask=bytearray(64); pos=lines.index('BITMAP')+1
 for y,row in enumerate(lines[pos:pos+h]):
  bits=int(row,16)
  for x in range(w):
   if bits & (1<<(len(row)*4-x-1)) and 0<=x+xo<8 and 0<=y+top<8: mask[(y+top)*8+x+xo]=1
 glyphs[chr(cp)]=bytes(mask)
notfound=set(chars)-glyphs.keys()
if notfound: raise ValueError('Missing BDF glyphs: '+''.join(sorted(notfound)))
for folder in ['classic','adambolt','nethack','ascii','akoimeexx','lomaka']:
 paltext=(S/'gfx'/folder/'master.pal.c').read_text(); pal=[int(x,16) for x in re.findall('0x([0-9a-fA-F]+)',paltext)]
 white=max(range(1,256),key=lambda i:sum((pal[i]>>s)&31 for s in [0,5,10])); black=next(i for i in range(1,256) if pal[i]==0)
 ext=bytearray()
 for c in chars:
  mask=glyphs[c]; ink=mask[8:]+bytes(8) if not any(mask[:8]) else mask; tile=bytearray(64)
  for y in range(7):
   for x in range(7):
    if ink[y*8+x]:tile[(y+1)*8+x+1]=black
  for i,v in enumerate(ink):
   if v:tile[i]=white
  ext.extend(tile)
 for p in (S/'gfx'/folder).glob('alphabet_*_8.c'):
  txt=p.read_text(); raw=bytearray(int(x,16) for x in re.findall('0x([0-9a-fA-F]+)',txt)); assert len(raw)==7680
  raw.extend(ext); name=re.search(r'char\s+(\w+)\[',txt)[1]
  p.write_text('const unsigned char '+name+'['+str(len(raw))+'] = {\n'+','.join(hex(x) for x in raw)+'\n};\n')
(S/'zh_text.h').write_text('''#ifndef ZH_TEXT_H
#define ZH_TEXT_H
#define ZH_GLYPH_COUNT '''+str(len(chars)+256)+'''
int zh_next(const char *&s);
int zh_len(const char *s);
bool zh_has(const char *s);
const char *zh_advance(const char *s,int count);
int zh_append(char *dst,const char *&src,int columns);
#endif
''')
(S/'zh_text.cpp').write_text('''#include "zh_text.h"
#include <string.h>
static const unsigned short cps[]={'''+','.join(str(ord(c)) for c in chars)+'''};
int zh_next(const char *&s){unsigned c=(unsigned char)*s++; if(c<0xc2)return c; unsigned cp=c; int n=0;
if(c<0xe0){cp=c&31;n=1;}else if(c<0xf0){cp=c&15;n=2;}else {return '?';}
for(int i=0;i<n;i++){unsigned b=(unsigned char)*s; if((b&192)!=128)return '?';cp=(cp<<6)|(b&63);s++;}
if(cp<256)return cp;int lo=0,hi=sizeof(cps)/2;while(lo<hi){int m=(lo+hi)/2;if(cps[m]<cp)lo=m+1;else hi=m;}return lo<(int)(sizeof(cps)/2)&&cps[lo]==cp?256+lo:'?';}
int zh_len(const char *s){int n=0;while(*s){zh_next(s);n++;}return n;}
bool zh_has(const char *s){while(*s)if((unsigned char)*s++>=0xc2)return true;return false;}
const char *zh_advance(const char *s,int n){while(n-->0 && *s)zh_next(s);return s;}
int zh_append(char *dst,const char *&src,int columns){int n=zh_len(dst);dst+=strlen(dst);while(*src&&n<columns){const char *p=src;zh_next(src);while(p<src)*dst++=*p++;n++;}*dst=0;return n;}
''')
(R/'analysis').mkdir(exist_ok=True)
(R/'analysis/translation_coverage.json').write_text(json.dumps({'applied':dict(stats),'glyphs':len(chars),'catalogs':{k:len(v) for k,v in [('data',D),('ui',U),('messages',M),('help',H)]},'unmatched_literals':missing},ensure_ascii=False,indent=2))
print('Staged',S,'glyphs',len(chars),'translated occurrences',sum(stats.values()))
