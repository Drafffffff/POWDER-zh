#include "zh_ui_font.h"
static const int zh_paper_size=10,zh_paper_rows=9,zh_paper_spacing=12;
static int zh_ui_step(int c,int size) {return c<128?(size==8?4:size<=10?5:6):c<256?8:(size==8?8:size<=10?10:12);}
static int zh_ui_width(const char *str,int size) {int w=0;while(*str)w+=zh_ui_step(zh_next(str),size);return w;}
// A full-line sentinel drives the existing paragraph builder's newline logic.
static int zh_pager_append(char *dst,const char *&src,int columns) {
    if(columns!=30)return zh_append(dst,src,columns);
    int width=zh_ui_width(dst,zh_paper_size),bytes=strlen(dst);
    while(*src) {
        const char *next=src;int c=zh_next(next),w=zh_ui_step(c,zh_paper_size);
        // Keep Latin words and bracketed button names together when possible.
        bool latin=(c>='A' && c<='Z')||(c>='a' && c<='z');
        bool prevlatin=bytes && ((dst[bytes-1]>='A' && dst[bytes-1]<='Z') || (dst[bytes-1]>='a' && dst[bytes-1]<='z'));
        if(width && (c=='[' || (latin && !prevlatin))) {
            const char *word=src;int wordwidth=0;
            while(*word && (c=='['?*word!=']':((*word>='A'&&*word<='Z')||(*word>='a'&&*word<='z')))) {
                wordwidth+=5;word++;
            }
            if(c=='[' && *word==']')wordwidth+=5;
            if(wordwidth<=220 && width+wordwidth>220)return columns;
        }
        if(width+w>220)return columns;
        memcpy(dst+bytes,src,next-src);bytes+=next-src;dst[bytes]=0;src=next;width+=w;
    }
    return 0;
}
// Shared native dot-matrix masks: 11px ink is cropped from the blank border
// of the 12px BDF. No strokes are scaled or discarded.
static const unsigned short *zh_ui_mask(int c,int size) {
    if(c<0 || c>=ZH_GLYPH_COUNT)c='?';
    return size==8?zh_ink8[c]:size==9?zh_ink9[c]:size==10?zh_ink10[c]:zh_ink11[c];
}
extern volatile unsigned zh_present_total,zh_present_overruns,zh_overrun_work,zh_overrun_line;
static void zh_wait_vblank();
extern bool zh_grouped_action_menu;
class ZHMenuPanel {
    u16 *saved,*indices,*nextmap;u8 *canvas,*patterns;int used;
    volatile u16 *map;u16 cursor;int previous_first,previous_select;unsigned previous_content;int font_size,page_rows,row_height,top_row,tile_rows,tile_count,canvas_height;bool grouped;
public:
    bool active;
    ZHMenuPanel(bool enable,int size=10,bool category_pages=false):saved(0),indices(0),nextmap(0),canvas(0),patterns(0),used(0),map(0),previous_first(-1),previous_select(-1),previous_content(0),font_size(size),page_rows(11),row_height(size==9?10:11),top_row(size==9?2:1),tile_rows(size==9?16:17),tile_count(tile_rows*14),canvas_height(tile_rows*8),grouped(category_pages && size==10),active(enable && glb_gfxmode==0) {
        if(!active)return;
        saved=new u16[tile_count];indices=new u16[tile_count];nextmap=new u16[tile_count];canvas=new u8[112*canvas_height];patterns=new u8[tile_count*64];
        map=(volatile u16*)(0x06000000+ham_bg[0].mi->blockid*0x800);
        for(int y=0;y<tile_rows;y++)for(int x=0;x<14;x++)saved[y*14+x]=map[(y+top_row)*32+x+15];
        volatile u16 *o=(volatile u16*)0x07000000;cursor=o[0];o[0]=0x0200;
    }
    void pageRange(int select,int n,int &first,int &last,int &page,int &pages)const {
        if(grouped && n==29) {
            page=select<11?0:select<20?1:2;pages=3;
            first=page==0?0:page==1?11:20;last=page==0?10:page==1?19:28;
        }else{page=select/page_rows;pages=(n+page_rows-1)/page_rows;first=page*page_rows;last=MIN(first+page_rows-1,n-1);}
    }
    int pageMove(int select,int n,int direction)const {
        if(!grouped || n!=29)return direction>0?MIN(page_rows,n-select-1):MAX(-page_rows,-select);
        int first,last,page,pages;pageRange(select,n,first,last,page,pages);
        int target=MAX(0,MIN(page+direction,pages-1));if(target==page)return 0;
        int next=grouped && n==29?(target==0?0:target==1?11:20):target*page_rows;
        int end=grouped && n==29?(target==0?10:target==1?19:28):MIN(next+page_rows-1,n-1);
        return MIN(next+select-first,end)-select;
    }
    void release(){for(int i=0;i<used;i++)glb_idxcount[indices[i]]--;used=0;}
    ~ZHMenuPanel(){if(!active)return;
        zh_wait_vblank();
        for(int y=0;y<tile_rows;y++)for(int x=0;x<14;x++)map[(y+top_row)*32+x+15]=saved[y*14+x];
        release();delete [] saved;delete [] indices;delete [] nextmap;delete [] canvas;delete [] patterns;
        ((volatile u16*)0x07000000)[0]=cursor;
    }
    __attribute__((section(".iwram"),long_call,noinline)) void text(int x,int y,const char *str,int colour,int limit,int size=10) {
        int black=glb_stdcolor[COLOUR_BLACK];
        while(*str && limit-->0) {
            int c=zh_next(str),step=zh_ui_step(c,size);if(x+step>110)break;
            const unsigned short *ink=zh_ui_mask(c,size);
            for(int j=-1;j<=size;j++) {
                unsigned bits=0;
                for(int oy=-1;oy<=1;oy++)if(j+oy>=0 && j+oy<size)bits|=ink[j+oy];
                bits=(bits<<2)|(bits<<1)|bits;
                if(y+j<0 || y+j>=canvas_height)continue;
                u8 *row=canvas+(y+j)*112;
                for(int i=-1;i<=size;i++)if((bits&(1<<(i+1))) && x+i>=0 && x+i<112)row[x+i]=black;
            }
            for(int j=0;j<size;j++) {
                unsigned bits=ink[j];u8 *row=canvas+(y+j)*112+x;
                if(y+j>=canvas_height)continue;
                for(int i=0;i<size;i++)if(bits&(1<<i))if(x+i<112)row[i]=colour;
            }
            x+=step;
        }
    }
    __attribute__((section(".iwram"),long_call,noinline)) void draw(const char **list,int select,int &first,int &last) {
        int n=0;while(list[n])n++;
        int page,pages;pageRange(select,n,first,last,page,pages);release();
        int black=glb_stdcolor[COLOUR_BLACK],white=glb_stdcolor[COLOUR_WHITE];
        // Keep the original room visible; use a one-pixel dark outline on text.
        unsigned content=n+white+(black<<8)+(glb_stdcolor[COLOUR_YELLOW]<<16);
        for(int i=first;i<=last;i++)for(const unsigned char *p=(const unsigned char*)list[i];*p;p++)content=content*33+*p;
        bool partial=font_size==10 && first==previous_first && content==previous_content;
        if(!partial) {
            memset(canvas,0,112*canvas_height);
            if(font_size==9)text(12,117,"A执行 B返回",white,12,9);
            else {
                const char *hint=grouped?(page==0?"探索 A执行 B返回":page==1?"战斗/物品 A执行 B返回":"休息/系统 A执行 B返回"):"A执行 B返回";
                text(12,126,hint,white,18,8);
            }
        }
        if(partial) {
            int changed[2]={previous_select,select};
            for(int k=0;k<2;k++)if(changed[k]>=first && changed[k]<=last) {
                int y=1+(changed[k]-first)*row_height;
                memset(canvas+(y-1)*112,0,(font_size+2)*112);
            }
        }
        for(int i=first;i<=last;i++) {
            // Tight rows share a black border. Restore adjacent outlines too.
            if(partial && (i<previous_select-1 || i>previous_select+1) && (i<select-1 || i>select+1))continue;
            int y=(font_size==9?2:1)+(i-first)*row_height;
            if(i==select)text(2,y,">",glb_stdcolor[COLOUR_YELLOW],1,font_size);
            text(12,y,list[i],i==select?glb_stdcolor[COLOUR_YELLOW]:white,20,font_size);
        }
        if(font_size!=9 || n>page_rows){char number[20];sprintf(number,"%d/%d",page+1,pages);text(82,font_size==9?0:1,number,white,5,font_size);}
        previous_first=first;previous_select=select;previous_content=content;
        u16 free_tiles[238];int free_count=0;
        for(int i=0;i<TILEARRAY && free_count<tile_count;i++)if(!glb_idxcount[i])free_tiles[free_count++]=i;
        // Hash table avoids comparing every tile with every preceding pattern.
        // Verify equal hashes with memcmp, so collisions never change pixels.
        short buckets[512];memset(buckets,0xff,sizeof(buckets));
        for(int y=0;y<tile_rows;y++)for(int x=0;x<14;x++) {
            u32 words[16];u16 *aligned=(u16*)words;u8 *tile=(u8*)words;
            for(int j=0;j<8;j++) {
                const u32 *src=(const u32*)(canvas+(y*8+j)*112+x*8);
                words[j*2]=src[0];words[j*2+1]=src[1];
            }
            unsigned hash=2166136261u;
            for(int j=0;j<32;j++)hash=((hash<<5)|(hash>>27))^aligned[j];
            unsigned slot=(hash^(hash>>16))&511;
            while(buckets[slot]>=0 && memcmp(patterns+buckets[slot]*64,tile,64))slot=(slot+1)&511;
            int k=buckets[slot]<0?used:buckets[slot];
            if(k==used) {
                int idx=used<free_count?free_tiles[used]:INVALID_TILEIDX;
                if(idx==INVALID_TILEIDX){nextmap[y*14+x]=used?indices[0]:saved[y*14+x];continue;}
                memcpy(patterns+used*64,tile,64);buckets[slot]=used;indices[used++]=idx;glb_idxcount[idx]++;
            }
            nextmap[y*14+x]=indices[k];
        }
        // Pattern generation and tile allocation touch RAM only. Commit the
        // complete tile payload and mapping during one fresh VBlank window.
        zh_wait_vblank();
        for(int i=0;i<used;i++) {
            int end=i+1;while(end<used && indices[end]==indices[end-1]+1)end++;
            ham_ReloadTileGfx(glb_bg1tiles,(const u16*)(patterns+i*64),indices[i],end-i);i=end-1;
        }
        for(int y=0;y<tile_rows;y++)for(int x=0;x<14;x++)map[(y+top_row)*32+x+15]=nextmap[y*14+x];
        zh_present_total++;if(*(volatile u16*)0x04000006<160){zh_present_overruns++;zh_overrun_line=*(volatile u16*)0x04000006;zh_overrun_work=used;}
    }
};
static ZHMenuPanel *zh_menu_panel=0;
// Page-flipped indexed bitmap: rasterize in RAM, transfer an inactive page
// during VBlank, then expose it. Never present forced blank or half a page.
static void zh_wait_vblank() {
    volatile u16 *line=(volatile u16*)0x04000006;
    while(*line>=160){}while(*line<160){}
}
static void zh_dma16(const void *src,volatile void *dst,int count) {
    *(volatile u32*)0x040000d4=(u32)src;
    *(volatile u32*)0x040000d8=(u32)dst;
    *(volatile u32*)0x040000dc=0x80000000u|count;
}
class ZHPaperScreen {
    u16 *backup,*buffer,regs[8],display;bool restored,presented;int front;
public:
    bool ready;
    ZHPaperScreen():backup(0),buffer(0),restored(false),presented(false),front(0),ready(false) {
        backup=new u16[39680];buffer=new u16[19200];
        if(!backup || !buffer)return;
        volatile u16 *v=(volatile u16*)0x06000000;
        zh_dma16((const void*)v,backup,39680);
        volatile u16 *r=(volatile u16*)0x04000020;
        for(int i=0;i<8;i++)regs[i]=r[i];
        display=*(volatile u16*)0x04000000;ready=true;
    }
    void restore(){if(restored || !presented)return;restored=true;
        volatile u16 *v=(volatile u16*)0x06000000;int offset=front?20480:0;
        // Restore memory outside the visible bitmap while that bitmap remains on screen.
        if(offset)zh_dma16(backup,v,offset);
        int end=offset+19200;
        if(end<39680)zh_dma16(backup+end,v+end,39680-end);
        zh_wait_vblank();
        zh_dma16(backup+offset,v+offset,19200);
        volatile u16 *r=(volatile u16*)0x04000020;for(int i=0;i<8;i++)r[i]=regs[i];
        *(volatile u16*)0x04000000=display;
        zh_present_total++;if(*(volatile u16*)0x04000006<160)zh_present_overruns++;
    }
    ~ZHPaperScreen(){restore();delete [] backup;delete [] buffer;}
    __attribute__((section(".iwram"),long_call,noinline)) void text(int x,int y,const char *str,int limit,int size=zh_paper_size) {
        u8 *v=(u8*)buffer;int white=glb_stdcolor[COLOUR_WHITE],black=glb_stdcolor[COLOUR_BLACK];
        while(*str && limit-->0){int c=zh_next(str),step=zh_ui_step(c,size);
            if(x+step>232)break;const unsigned short *ink=zh_ui_mask(c,size);
            for(int j=0;j<size;j++) {
                unsigned bits=ink[j];u8 *row=v+(y+j+1)*240+x+1;
                if(y+j+1<160)for(int i=0;i<size;i++)if(bits&(1<<i))row[i]=black;
            }
            for(int j=0;j<size;j++) {
                unsigned bits=ink[j];u8 *row=v+(y+j)*240+x;
                if(y+j<160)for(int i=0;i<size;i++)if(bits&(1<<i))row[i]=white;
            }
            x+=step;
        }
    }
    __attribute__((section(".iwram"),long_call,noinline)) void draw(char **lines,int count,int first) {
        u8 *v=(u8*)buffer;
        // Decode one 16px texture period per row, then copy repeated spans.
        // This retains the exact parchment pixels without per-pixel division.
        for(int y=0;y<160;y++) {
            u8 *row=v+y*240;
            if(y<8 || y>=152){memset(row,glb_stdcolor[COLOUR_BLACK],240);continue;}
            int tile=y<24?TILE_SCROLL_TOP:y>=136?TILE_SCROLL_BOTTOM:TILE_SCROLL_BACK;
            int ty=(y-8)&15;
            const u8 *src=&glb_tilesets[glb_tileset].dungeon[tile*256]+(ty/8)*128+(ty&7)*8;
            memcpy(row,src,8);memcpy(row+8,src+64,8);
            memcpy(row+16,row,16);memcpy(row+32,row,32);
            memcpy(row+64,row,64);memcpy(row+128,row,112);
        }
        for(int row=0;row<zh_paper_rows && first+row<count;row++)text(10,26+row*zh_paper_spacing,lines[first+row],50);
        char footer[64];sprintf(footer,"%d/%d  上下滚动  A/B返回",first+1,MAX(1,count-zh_paper_rows+1));text(10,147,footer,40,9);
        int next=presented?1-front:1;
        zh_wait_vblank();
        zh_dma16(buffer,(volatile void*)(next?0x0600a000:0x06000000),19200);
        if(!presented) {
            volatile u16 *r=(volatile u16*)0x04000020;
            r[0]=256;r[1]=0;r[2]=0;r[3]=256;r[4]=r[5]=r[6]=r[7]=0;
        }
        *(volatile u16*)0x04000000=0x0404|(next?0x10:0);
        front=next;presented=true;
        zh_present_total++;if(*(volatile u16*)0x04000006<160)zh_present_overruns++;
    }
};
static bool zh_read_paper(char **lines,int count,int start) {
    ZHPaperScreen paper;if(!paper.ready)return false;int first=MAX(0,MIN(start-zh_paper_rows/2,count-zh_paper_rows));paper.draw(lines,count,first);
    while(ctrl_anyrawpressed() && !hamfake_forceQuit())hamfake_awaitEvent();
    hamfake_clearKeyboardBuffer();
    while(!hamfake_forceQuit()) {
        if(!gfx_isnewframe())continue;
        if(ctrl_hit(BUTTON_A)||ctrl_hit(BUTTON_B))break;
        int dx=0,dy=0;
        if(ctrl_hit(BUTTON_R))dy=zh_paper_rows;else if(ctrl_hit(BUTTON_L))dy=-zh_paper_rows;else ctrl_getdir(dx,dy);
        int next=MAX(0,MIN(first+dy,MAX(0,count-zh_paper_rows)));
        if(next!=first){first=next;paper.draw(lines,count,first);}
    }
    return true;
}
