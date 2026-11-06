"""Native32 text callback, mutable opaque providers, and defined external state."""
from tools.experiments import game_white_text_crossfade_candidates as source
HEADERS='''#include <ultra64.h>
typedef struct {
    u8 tag; u8 pad01[3]; u8 *source; u8 active; u8 pad09[3];
    u8 *start; u8 *next; u8 length, index; u8 pad16[2];
    u8 *buffers[2]; u8 *payload; s8 kind; u8 flags; u8 pad26[2];
} TextDescriptorFC5F0;
void func_1504332C(u8,u8,u8,u8);
void func_15042D94(s32,s32,u8,s32,...);
extern s32 D_800BE9E4;
'''

def program(body):return HEADERS+body+r'''
typedef struct{u8 header[40];TextDescriptorFC5F0 text;} Owner;
typedef char descriptor_size[sizeof(TextDescriptorFC5F0)==40?1:-1];
typedef char descriptor_offset[__builtin_offsetof(Owner,text)==40?1:-1];
typedef char payload_offset[__builtin_offsetof(TextDescriptorFC5F0,payload)==32?1:-1];
typedef struct{u32 kind,a,b,c,d;} Call;
typedef struct{Owner owner;u8 payload;Call calls[4];u32 used;} State;
static State actual,expected;static u8 buffers[4][4];static u32 mutation;
s32 D_800BE9E4;
static s32 (*callback)(u8 *)=func_150D0534;
static void effect(State*s,u32 n){
    if(mutation&1)s->owner.text.index^=1;
    if(mutation&2){s->owner.text.buffers[0]=buffers[(n+1)&3];s->owner.text.buffers[1]=buffers[(n+2)&3];}
    if(mutation&4)s->payload^=0xa5;
}
static void capture(State*s,u32 kind,u32 a,u32 b,u32 c,u32 d){
    u32 n=s->used++;if(n>=4)__builtin_trap();s->calls[n]=(Call){kind,a,b,c,d};effect(s,n);
}
void func_1504332C(u8 a,u8 b,u8 c,u8 d){capture(&actual,0,a,b,c,d);}
void func_15042D94(s32 a,s32 b,u8 c,s32 d,...){capture(&actual,1,(u32)a,(u32)b,c,(u32)d);}
static void initialize(State*s,u32 count,u32 flags,u32 index){
    u32 i;u8*p=(u8*)s;for(i=0;i<sizeof(*s);i++)p[i]=0;
    s->payload=(u8)count;s->owner.text.active=(u8)flags;s->owner.text.index=(u8)index;
    s->owner.text.buffers[0]=buffers[0];s->owner.text.buffers[1]=buffers[1];s->owner.text.payload=&s->payload;
}
static void reference(void){
    s32 count;u32 alpha,other;
    if(expected.owner.text.active%2)expected.payload=20;
    count=expected.payload<128?expected.payload:(s32)expected.payload-256;
    alpha=count>0?((u32)count*12)%256:0;other=255-alpha;
    if(count>0)expected.payload=(u8)((u32)count-(u32)D_800BE9E4);
    if(other){capture(&expected,0,255,255,255,other);capture(&expected,1,20,20,128,(u32)expected.owner.text.buffers[expected.owner.text.index]);}
    if(alpha){capture(&expected,0,255,255,255,alpha);capture(&expected,1,20,20,128,(u32)expected.owner.text.buffers[1-expected.owner.text.index]);}
}
static int same(void){
    u32 i;if(actual.owner.text.payload!=&actual.payload||expected.owner.text.payload!=&expected.payload)return 0;
    actual.owner.text.payload=expected.owner.text.payload;
    for(i=0;i<sizeof(State);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])return 0;
    return 1;
}
static int run(void){
    const u32 ticks[]={0,1,2,0x80000000u,0xffffffffu};u32 c,f,i,t,m;
    for(c=0;c<256;c++)for(f=0;f<2;f++)for(i=0;i<2;i++)for(t=0;t<5;t++)for(m=0;m<4;m++){
        mutation=(u32[]){0,1,3,7}[m];D_800BE9E4=(s32)ticks[t];initialize(&actual,c,f,i);initialize(&expected,c,f,i);reference();
        if(callback((u8*)&actual.owner)!=1||!same())return 1;
    }
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
