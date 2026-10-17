#!/usr/bin/env python3
"""Build POWDER using a project-local ARM GCC and libgba; no global installs."""
import pathlib, subprocess, re, concurrent.futures, sys, json, os
R=pathlib.Path(__file__).resolve().parents[1]
S=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else R/'source'
stress_build=os.environ.get('POWDER_STRESS_BUILD')=='1'
B=R/'build'/('gba_'+S.name+('_stress' if stress_build else '')); B.mkdir(parents=True,exist_ok=True)
T=R/'toolchain'; prefix=str(next(T.glob('xpack-arm*/bin/arm-none-eabi-gcc')))[:-3]
cc=prefix+'gcc'; cxx=prefix+'g++'
flags=['-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-Os','-ffunction-sections','-fdata-sections','-fno-short-enums','-DNO_HAM','-I'+str(S/'port/gba'),'-I'+str(S),'-I'+str(T/'libgba/include')]
if stress_build:flags.append('-DFORCESTRESSTEST')
make=(S/'port/gba/Makefile').read_text(); section=make.split('CPPFILES\t:=')[1].split('SFILES')[0]
files=[(S/'port/gba'/x).resolve() for x in re.findall(r'[./\w]+\.cpp',section)]
libsrc=T/'libgba/src'
files += [libsrc/x for x in ['interrupt.c','input.c','IntrWait.c','CpuSet.c','Compression.c','AffineSet.c','fade.c','InterruptDispatcher.s','Div.s','DivArm.s','Sqrt.s','Reset.s','ArcTan.s']]
files += [T/'devkitarm-crtls/gba_crt0.s']
if (S/'zh_text.cpp').exists(): files.append(S/'zh_text.cpp')
(B/'syscalls.c').write_text('''#include <stddef.h>\n#include <errno.h>\nextern char __eheap_start, __eheap_end;\nvoid *fake_heap_end;\nvoid *_sbrk(ptrdiff_t n) { static char *p; if(!p)p=&__eheap_start; char *q=p; if(n>0 && p+n>&__eheap_end){errno=ENOMEM;return (void*)-1;}p+=n; return q;}\nint _write(int f,const void *p,int n){return n;}\nint _read(int f,void *p,int n){return 0;}\nint _kill(int p,int s){return -1;}\nint _getpid(void){return 1;}\nint _close(int f){return -1;}\nint _fstat(int f,void *p){return -1;}\nint _isatty(int f){return 0;}\nint _lseek(int f,int a,int b){return -1;}\nint _open(const char *p,int f,...){return -1;}\nvoid _exit(int n){for(;;){}}\nvoid _init(void){}\nvoid _fini(void){}\n''')
files += [B/'syscalls.c']
(B/'new.cpp').write_text('''#include <stdlib.h>\nvoid *operator new(unsigned n){return malloc(n);}\nvoid *operator new[](unsigned n){return malloc(n);}\nvoid operator delete(void *p) throw(){free(p);}\nvoid operator delete[](void *p) throw(){free(p);}\nextern "C" void __cxa_pure_virtual(){for(;;){}}\n''')
files += [B/'new.cpp']
def compile_one(pair):
 i,f=pair; obj=B/(str(i)+'_'+f.stem+'.o')
 # Always compile: gbamain and all_bitmaps include generated source files.
 opts=flags+(['-std=gnu++98','-fpermissive','-fno-exceptions','-fno-rtti','-fno-threadsafe-statics','-fno-use-cxa-atexit'] if f.suffix=='.cpp' else [])
 if f.suffix=='.s': opts=flags+['-x','assembler-with-cpp','-marm']
 p=subprocess.run([cxx if f.suffix=='.cpp' else cc,*opts,'-c',str(f),'-o',str(obj)],capture_output=True,text=True)
 if p.returncode: print(f.name+'\n'+p.stderr); raise RuntimeError(f)
 print('compiled',f.name,flush=True); return obj
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: objs=list(pool.map(compile_one,enumerate(files)))
elf=B/'powder.elf'
linker=B/'gba_cart.ld'
linker.write_text((T/'devkitarm-crtls/gba_cart.ld').read_text().replace('*(.iwram)','*(.iwram) *(.iwram_movement)'))
subprocess.run([cxx,*flags,'-nostartfiles','-Wl,-T,'+str(linker),'-Wl,-Map,'+str(B/'powder.map'),'-Wl,--gc-sections','-Wl,--no-enum-size-warning',*[str(x) for x in objs],'-Wl,--start-group','-lc','-lm','-lnosys','-lgcc','-Wl,--end-group','-o',str(elf)],check=True)
subprocess.run([prefix+'objcopy','-O','binary',str(elf),str(B/'powder.gba')],check=True)
rom=bytearray((B/'powder.gba').read_bytes()); orig=(R/'original/powder118.gba').read_bytes()
rom[4:0xa0]=orig[4:0xa0]; rom[0xa0:0xac]=b'POWDER118ZH\0'; rom[0xac:0xbe]=orig[0xac:0xbe]; rom[0xbd]=(-sum(rom[0xa0:0xbd])-0x19)&255
(B/'powder.gba').write_bytes(rom)
print('ROM', B/'powder.gba', len(rom))

# Runtime tests read EWRAM counters using exact ELF symbol addresses.
nm=subprocess.run([prefix+'nm','-n',str(elf)],check=True,capture_output=True,text=True).stdout
symbols={}
for line in nm.splitlines():
 parts=line.split()
 if len(parts)==3 and parts[2] in ('zh_present_total','zh_present_overruns','zh_overrun_work','zh_overrun_line','zh_world_rebuilds'):symbols[parts[2]]=int(parts[0],16)
(B/'renderer_symbols.json').write_text(json.dumps(symbols,indent=2)+'\n')

world={parts[2]:int(parts[0],16) for line in nm.splitlines() if len(parts:=line.split())==3 and parts[2]=='glbStressTest'}
(B/'world_symbols.json').write_text(json.dumps(world,indent=2)+'\n')
