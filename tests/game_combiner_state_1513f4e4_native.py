"""SDK native32 dynamic combine macros, pointer return and signed cache."""
from functools import lru_cache
from tools.experiments import game_combiner_state_1513f4e4_candidates as c
from tools.tests import game_combiner_state_1513f4e4_oracle as g
from tools.tests.game_record_motion_update_1513e6e8_native import digest

@lru_cache(None)
def rows():
    rows=[]
    for case in g.native_cases():
        m=g.reference(g.fixture(case,'little'),case,'little');memory=m['memory']
        h=digest(g.ram.data(memory,g.OUTPUT,64)+g.ram.data(memory,g.DIRTY,16)+g.ram.data(memory,g.TABLE,4096)+g.ram.data(memory,g.CACHE,2))
        row=(case.index,case.dirty,case.cache,case.same,g.u32(g.selected(case.index,case)),case.pattern,case.seed,h,m['value'])
        rows.append('{'+','.join('0x%Xu'%v for v in row)+'}')
    return ',\n'.join(rows)

def harness(body=None):
    return '#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n'+(c.SELECTED if body is None else body)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef char Gfx64[sizeof(Gfx)==8?1:-1];
typedef struct{u32 index,dirty,cache,same,result,pattern,seed,hash,answer;}Case;
static const Case cases[]={'''+rows()+r'''};
static Gfx output[8] __attribute__((section(".output"),used,aligned(8)));
static u8 dirty[16] __attribute__((section(".dirty"),used,aligned(4)));
u8 D_800A4BA8[256][16] __attribute__((section(".table"),used,aligned(8)));
s16 D_800DD1BE __attribute__((section(".cache"),used,aligned(2)));
static u32 helper_calls,expected_index,bad_call;
static s16 answer;
s16 func_15143044(u8 index,s32 mode){helper_calls++;if(index!=expected_index||mode!=0)bad_call=1;return answer;}
static void wr(u8 *p,u32 v){p[0]=(u8)v;p[1]=(u8)(v>>8);}
static int run(void){u32 i,j,h;Gfx *result;Gfx *(* volatile callback)(Gfx *,u8,u8 *)=func_1513F4E4;
    if((u32)output!=0x50000||(u32)dirty!=0x60000||(u32)D_800A4BA8!=0x800A4BA8||(u32)&D_800DD1BE!=0x800DD1BE)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        const Case *c=&cases[i];for(j=0;j<64;j++)((u8 *)output)[j]=(u8)(j*29+c->seed*11+90);
        for(j=0;j<16;j++)dirty[j]=(u8)(j*29+c->seed*11+90);
        for(j=0;j<4096;j++)((u8 *)D_800A4BA8)[j]=c->pattern==0?(u8)(j*29+c->seed*11+90):c->pattern==1?255:c->pattern==2?0:(u8)(j%2?(1u<<(j%8)):(255u^(1u<<(j%8))));
        wr((u8 *)&D_800DD1BE,c->same?c->result:c->cache);dirty[0]=(u8)c->dirty;answer=(s16)c->result;expected_index=c->index&255u;helper_calls=bad_call=0;
        result=callback(output,(u8)c->index,dirty);h=2166136261u;
        for(j=0;j<64;j++)h=(h^((u8 *)output)[j])*16777619u;
        for(j=0;j<16;j++)h=(h^dirty[j])*16777619u;
        for(j=0;j<4096;j++)h=(h^((u8 *)D_800A4BA8)[j])*16777619u;
        for(j=0;j<2;j++)h=(h^((u8 *)&D_800DD1BE)[j])*16777619u;
        if((u32)result!=c->answer||h!=c->hash||helper_calls!=1||bad_call)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.output=0x50000,--section-start=.dirty=0x60000,--section-start=.table=0x800A4BA8,--section-start=.cache=0x800DD1BE']
