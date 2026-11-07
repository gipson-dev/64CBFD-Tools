"""Native32 SDK body through the retained table's selected typed slot."""
from functools import lru_cache
from tools.experiments import game_record_motion_update_1513e6e8_candidates as c
from tools.tests import game_record_motion_update_1513e6e8_oracle as g

def digest(data):
    value=2166136261
    for byte in data:value=((value^byte)*16777619)&0xFFFFFFFF
    return value

@lru_cache(None)
def rows():
    result=[]
    for case in g.native_cases():
        initial=g.fixture(case,'little');e=g.reference(initial,case,'little');m=e['memory'];h=digest(g.ram.data(m,g.RESOURCE,512)+g.ram.data(m,g.TIME,4))
        result.append('{'+','.join('0x%Xu'%v for v in(case.flags,case.time,case.pattern,case.seed,h))+'}')
    return ',\n'.join(result)

def harness(body=None):
    patterns=','.join('{'+','.join('0x%Xu'%v for v in p)+'}'for p in g.PATTERNS)
    return '#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n'+(c.SELECTED if body is None else body)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef struct{u32 flags,time,pattern,seed,hash;}Case;
static const Case cases[]={'''+rows()+r'''};
static const u32 patterns[5][6]={'''+patterns+r'''};
static const u32 offsets[]={0x34,0x38,0x3C,0x40,0x44,0x48,0x4C,0x50,0x54,0x118,0x11C,0x120,0x124,0x128,0x12C,0x130,0x134,0x138,0x13C};
static u8 resource[512] __attribute__((section(".resource"),used,aligned(8)));
f32 D_800BE9A4 __attribute__((section(".time"),used,aligned(4)));
static s32(*callbacks[42])(u8 *) __attribute__((section(".callbacks"),used,aligned(4)))={0,func_1513E6E8};
static void wr(u8 *p,u32 value){u32 i;for(i=0;i<4;i++){p[i]=(u8)value;value>>=8;}}
static int run(void){u32 i,j,h,mxcsr;s32 answer;s32(* volatile callback)(u8 *)=callbacks[1];
    __asm__ volatile("stmxcsr %0":"=m"(mxcsr));
    if(mxcsr&0xE040u)return 2;
    if((u32)resource!=0x30000||(u32)&D_800BE9A4!=0x800BE9A4||(u32)callbacks!=0x80089CB8)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        const Case *c=&cases[i];for(j=0;j<512;j++)resource[j]=(u8)(j*29+c->seed*11+90);
        for(j=0;j<sizeof(offsets)/sizeof(offsets[0]);j++)wr(resource+offsets[j],patterns[c->pattern][(j+c->seed)%6]);
        wr(resource+0x58,c->flags);wr((u8 *)&D_800BE9A4,c->time);answer=callback(resource);h=2166136261u;
        for(j=0;j<512;j++)h=(h^resource[j])*16777619u;
        for(j=0;j<4;j++)h=(h^((u8 *)&D_800BE9A4)[j])*16777619u;
        if(answer!=1||h!=c->hash)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.resource=0x30000,--section-start=.time=0x800BE9A4,--section-start=.callbacks=0x80089CB8']
