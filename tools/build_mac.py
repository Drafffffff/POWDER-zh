#!/usr/bin/env python3
from pathlib import Path
import subprocess,re,concurrent.futures,shlex,shutil
R=Path(__file__).resolve().parents[1];S=R/'build/mac_src';shutil.copytree(R/'source',S,dirs_exist_ok=True);B=R/'build/mac_native';B.mkdir(parents=True,exist_ok=True)
subprocess.run(['bash','rebuild.sh'],cwd=S/'gfx',check=True)
config='/opt/homebrew/opt/sdl12-compat/bin/sdl-config'
cflags=shlex.split(subprocess.check_output([config,'--cflags'],text=True));libs=shlex.split(subprocess.check_output([config,'--libs'],text=True))
make=(S/'port/linux/Makefile').read_text().split('OFILES =',1)[1].split('PREMAKE',1)[0]
files=[(S/'port/linux'/x.replace('.o','.cpp')).resolve() for x in re.findall(r'[.\w/]+\.o',make)]
flags=['-O2','-std=gnu++98','-Wno-c++11-narrowing','-Wno-deprecated-declarations','-DLINUX','-DCHANGE_WORK_DIRECTORY','-I'+str(S/'port/sdl'),*cflags]
def compile(pair):
 i,f=pair;o=B/(str(i)+'_'+f.stem+'.o')
 p=subprocess.run(['clang++',*flags,'-c',str(f),'-o',str(o)],capture_output=True,text=True)
 if p.returncode:print(p.stderr);raise RuntimeError(f)
 return o
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:objs=list(pool.map(compile,enumerate(files)))
subprocess.run(['clang++',*[str(o) for o in objs],*libs,'-o',str(B/'powder')],check=True)
print(B/'powder')
