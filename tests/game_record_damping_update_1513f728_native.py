"""SDK native32 C through retained callback slot25; ordinary finite inputs."""
from functools import lru_cache
from tools.experiments import game_record_damping_update_1513f728_candidates as c
from tools.tests import game_record_damping_update_1513f728_oracle as g
from tools.tests.game_record_motion_update_1513e6e8_native import digest

@lru_cache(None)
def rows():
    result=[]
    for case in g.native_cases():
        initial=g.fixture(case,'little');m=g.reference(initial,case,'little')['memory']
        h=digest(g.ram.data(m,g.RESOURCE,512)+g.ram.data(m,g.TIME,80))
        result.append('{'+','.join('0x%Xu'%v for v in(case.ticks,case.time,case.inverse,case.damping,case.pattern,case.seed,h))+'}')
    return ',\n'.join(result)

def harness(body=None):
    patterns=','.join('{'+','.join('0x%Xu'%v for v in p)+'}'for p in g.PATTERNS)
    offsets=','.join(hex(off)for off in g.OFFSETS)
    return '#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n'+(c.SELECTED if body is None else body)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef struct{u32 ticks,time,inverse,damping,pattern,seed,hash;}Case;
static const Case cases[]={'''+rows()+r'''};
static const u32 patterns[5][6]={'''+patterns+r'''};
static const u32 offsets[]={'''+offsets+r'''};
static u8 resource[512] __attribute__((section(".resource"),used,aligned(8)));
static u8 globals[80] __attribute__((section(".globals"),used,aligned(4)));
__asm__(".globl D_800BE9A4\n.set D_800BE9A4,globals\n.globl D_800BE9A8\n.set D_800BE9A8,globals+4\n.globl D_800BE9E4\n.set D_800BE9E4,globals+64\n");
static s32(*callbacks[42])(u8 *) __attribute__((section(".callbacks"),used,aligned(4)))={[25]=func_1513F728};
static void wr(u8 *p,u32 v){u32 i;for(i=0;i<4;i++){p[i]=(u8)v;v>>=8;}}
static int run(void){u32 i,j,h,mxcsr;s32 answer;s32(* volatile callback)(u8 *)=callbacks[25];
    __asm__ volatile("stmxcsr %0":"=m"(mxcsr));if(mxcsr&0xE040u)return 2;
    if((u32)resource!=0x30000||(u32)globals!=0x800BE9A4||(u32)&D_800BE9A8!=0x800BE9A8||(u32)&D_800BE9E4!=0x800BE9E4||(u32)callbacks!=0x80089CB8)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        const Case *c=&cases[i];for(j=0;j<512;j++)resource[j]=(u8)(j*29+c->seed*11+90);
        for(j=0;j<80;j++)globals[j]=(u8)(j*29+c->seed*11+90);
        for(j=0;j<sizeof(offsets)/sizeof(offsets[0]);j++)wr(resource+offsets[j],patterns[c->pattern][(j+c->seed)%6]);
        wr(resource+0x120,c->damping);wr(globals,c->time);wr(globals+4,c->inverse);wr(globals+64,c->ticks);
        answer=callback(resource);h=2166136261u;
        for(j=0;j<512;j++)h=(h^resource[j])*16777619u;
        for(j=0;j<80;j++)h=(h^globals[j])*16777619u;
        if(answer!=1||h!=c->hash)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.resource=0x30000,--section-start=.globals=0x800BE9A4,--section-start=.callbacks=0x80089CB8']
