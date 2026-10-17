#!/usr/bin/env python3
"""Validate translation tokens, data coverage and UTF-8 line buffer boundaries."""
import json,re,pathlib,collections,subprocess,hashlib
R=pathlib.Path(__file__).resolve().parents[1]
printf=re.compile(r'%(?:[-+ #0]*)(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hljztL])?[diouxXfFeEgGaAcspn%]')
token=re.compile(printf.pattern+r'|%[MI][A-Za-z]|%B\d|%[A-Za-z]')
errors=[]; counts={}
for p in (R/'translations').glob('*_zh.json'):
 d=json.loads(p.read_text());counts[p.name]=len(d)
 for eng,zh in d.items():
  a=token.findall(eng); b=token.findall(zh)
  if collections.Counter(a)!=collections.Counter(b):errors.append([p.name,eng,a,b])
  if printf.findall(eng)!=printf.findall(zh):errors.append(['printf-order',p.name,eng])
assert not errors,repr(errors[:20])
orig=R/'original/powder118.gba';assert hashlib.sha256(orig.read_bytes()).hexdigest()=='20bf244560265e8215ea9df2d23c3c85a93bb49f1a91010a230d0d125cc3b654'
# All meaningful source.txt values are translated. Single-character shortcuts stay intact.
D=json.loads((R/'translations/data_zh.json').read_text())
values={bytes(m[1],'utf8').decode('unicode_escape') for m in re.finditer(r'"((?:\\.|[^"\\])*)"',(R/'source/source.txt').read_text())}
unmapped=[v for v in values if len(v)>1 and re.search('[A-Za-z]',v) and v not in D and v != "><0|V|"]
assert not unmapped,repr(unmapped)
B=R/'build';S=B/'zh_src'
(B/'zh_text_test.cpp').write_text(r'''#include "zh_text.h"
#include <cstdlib>
#define assert(x) do{if(!(x))abort();}while(0)
#include <cstring>
int main(){
 assert(zh_len("新游戏")==3);assert(zh_len("A新B游戏")==5);
 const char *s="新游戏";int g=zh_next(s);assert(g>=256&&g<ZH_GLYPH_COUNT);assert(zh_len(s)==2);
 const char *sym="\200\213";assert(zh_next(sym)==128);assert(zh_next(sym)==139);
 struct{char dst[30*3+4];char guard[8];} x;memset(&x,0,sizeof(x));memset(x.guard,42,8);
 s="新新新新新新新新新新新新新新新新新新新新新新新新新新新新新新新新";
 assert(zh_append(x.dst,s,30)==30);assert(strlen(x.dst)==90);assert(zh_len(s)==2);
 for(int i=0;i<8;i++)assert(x.guard[i]==42);
 char y[10]={};zh_append(y,s,2);assert(zh_len(y)==2);assert(!*s);
 return 0;}
''')
subprocess.run(['c++','-std=c++98','-fsanitize=address,undefined','-I'+str(S),str(B/'zh_text_test.cpp'),str(S/'zh_text.cpp'),'-o',str(B/'zh_text_test')],check=True)
subprocess.run([str(B/'zh_text_test')],check=True)
# The reader now wraps by pixels; protect its UTF-8 buffers and button tokens.
helper=(R/'tools/ui_zh_overlay.inc').read_text().split('class ZHMenuPanel')[0]
(B/'zh_ui_test.cpp').write_text('#include "zh_text.h"\n#include <cstring>\n#include <cstdlib>\n#define assert(x) do{if(!(x))abort();}while(0)\n'+helper+r'''
int main(){
 const char *src="按上下方向键滚动文字， [Select] 与 [Start] 是按钮。abcdefghijklmnopqrstuvwxyz 中文中文中文中文中文中文中文中文中文中文中文中文中文中文中文中文中文中文";
 int lines=0;bool button=false;
 while(*src){
  struct{char text[94];char guard[8];} row;memset(&row,0,sizeof(row));memset(row.guard,42,8);
  const char *before=src;int result=zh_pager_append(row.text,src,30);
  assert(src!=before);assert(result==0||result==30);
  assert(zh_ui_width(row.text,zh_paper_size)<=220);assert(strlen(row.text)<94);
  for(int i=0;i<8;i++)assert(row.guard[i]==42);
  if(strstr(row.text,"[Select]"))button=true;
  assert(++lines<100);
 }
 assert(button);
 const char *hint="上下滚动返回执行";
 while(*hint){const unsigned short *ink=zh_ui_mask(zh_next(hint),9);bool has=false;
  for(int y=0;y<12;y++){if(y>=9)assert(ink[y]==0);assert((ink[y]&~511)==0);has|=ink[y]!=0;}assert(has);
 }
 const char *small="探索战斗其他A执行B返回";
 while(*small){const unsigned short *ink=zh_ui_mask(zh_next(small),8);bool has=false;
  for(int y=0;y<12;y++){if(y>=8)assert(ink[y]==0);assert((ink[y]&~255)==0);has|=ink[y]!=0;}assert(has);
 }
 return 0;
}
''')
subprocess.run(['c++','-std=c++98','-fsanitize=address,undefined','-I'+str(S),str(B/'zh_ui_test.cpp'),str(S/'zh_text.cpp'),'-o',str(B/'zh_ui_test')],check=True)
subprocess.run([str(B/'zh_ui_test')],check=True)
report={'catalogs':counts,'catalog_entries':sum(counts.values()),'format_tokens':'pass','pixel_wrap_and_9px_hint_bounds':'pass','source_data_meaningful_coverage':'pass','utf8_and_buffer_boundaries':'pass','original_sha256':'unchanged'}
(R/'analysis/zh_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
