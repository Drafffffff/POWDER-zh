#include <mgba/core/core.h>
#include <mgba/internal/arm/arm.h>
#include <mgba-util/vfs.h>
#include <stdio.h>
struct mCore *GBACoreCreate(void);
int main(int argc,char **argv){struct mCore*c=GBACoreCreate();c->init(c);mCoreInitConfig(c,0); color_t pixels[256*160];c->setVideoBuffer(c,pixels,256);struct VFile*f=VFileOpen(argv[1],0);c->loadROM(c,f);c->reset(c);struct ARMCore*a=c->cpu;for(int i=0;i<100;i++){c->runFrame(c);printf("%d pc=%08x sp=%08x lr=%08x r0=%08x r1=%08x mode=%x disp=%x\n",i,a->gprs[15],a->gprs[13],a->gprs[14],a->gprs[0],a->gprs[1],a->cpsr.packed,c->busRead16(c,0x4000000));}return 0;}
