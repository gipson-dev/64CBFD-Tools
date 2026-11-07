"""Native32 SDK graphics macros, valid view indices and independent byte hashes."""
from functools import lru_cache
import itertools
from tools.experiments import game_view_resource_draw_1513b83c_candidates as c
from tools.tests import game_view_resource_draw_1513b83c_oracle as g
def cases():
    for flags,view,index,outcome in itertools.product((0,2),(0,7,31),(-1,0,2,6),(0,1)):
        yield g.Case(flags=flags,view=view,index=index,outcome=outcome,page=view&1)
    for mask,view in itertools.product((0,1,2,0x7F,0x80,0xFE,0xFF),(0,1,3,7,8,31)):
        yield g.Case(flags=2,mask=mask,view=view,seed=1)
    for index,outcome in itertools.product(range(7),(0,0x80000000)):yield g.Case(index=index,outcome=outcome,seed=2)
    for mutation,view,outcome in itertools.product((1,4),(0,7,31),(0,1)):yield g.Case(index=0,mutation=mutation,view=view,outcome=outcome)
def digest(values):
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xFFFFFFFF
    return h
@lru_cache(None)
def rows():
    result=[]
    for case in cases():
        e=g.reference(g.fixture(case,'little'),case,'little');trace=[]
        for t,a in e['calls']:
            for v in(t,len(a),*a):trace.extend(g.u32(v).to_bytes(4,'little'))
        observed=g.data(e['memory'],g.RESOURCE,8192)+g.data(e['memory'],g.CURSOR,256)+bytes([e['memory'][g.PAGE]])
        values=(case.flags,case.mask,case.index,case.view,case.page,case.outcome,case.mutation,case.seed,digest(observed),digest(trace),e['value'])
        result.append('{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}')
    return ',\n'.join(result)
def harness(body=None):
    wrappers='\n'.join('static s32 cb%d(u8 *resource,s16 view){return callback(0x%X,resource,view);}'%(i,t)for i,t in enumerate(g.CALLBACKS))
    return '#include <ultra64.h>\nextern s32 (*D_80089C28[])(u8 *,s16);\nextern u8 D_800BE9C0;\n'+(c.SELECTED if body is None else body)+r'''
typedef char GfxSize[sizeof(Gfx)==8?1:-1];
typedef char MatrixSize[sizeof(Mtx)==64?1:-1];
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef struct{u32 flags,mask,index,view,page,outcome,mutation,seed,hash,trace,value;}Case;
static const Case cases[]={
'''+rows()+r'''};
static u32 resourceWords[2048] __attribute__((section(".resource"),aligned(8)));
static u32 commandWords[64] __attribute__((section(".commands"),aligned(8)));
static u8 *resource=(u8 *)resourceWords,*commands=(u8 *)commandWords;
u8 D_800BE9C0;static const Case *current;static u32 traceHash;
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
static void wr(u8 *p,u32 v){u32 i;for(i=0;i<4;i++){p[i]=(u8)v;v>>=8;}}
static s32 callback(u32 t,u8 *record,s16 view){
    mix(t);mix(2);mix((u32)record);mix((u32)(s32)view);
    if(current->mutation==1){D_800BE9C0=1;wr(resource+0x58+16+(s32)(s16)current->view*4,0x13579BDF);wr(resource+0x54,0x2468ACE0);}
    if(current->mutation==4){resource[0x12]=255;resource[0x49]=0;}
    return(s32)current->outcome;
}
'''+wrappers+r'''
s32 (*D_80089C28[])(u8 *,s16)={cb0,cb1,cb2,cb3,cb4,cb5,cb6};
static u32 hash(u32 h,u8 *p,u32 n){u32 i;for(i=0;i<n;i++)h=(h^p[i])*16777619u;return h;}
static int run(void){u32 i,j,h,v;
    if((u32)resource!=0x50000||(u32)commands!=0x60000)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];for(j=0;j<8192;j++)resource[j]=(u8)(j*29+current->seed*11+90);for(j=0;j<256;j++)commands[j]=(u8)(j*29+current->seed*11+90);
        resource[0x10]=(u8)current->flags;resource[0x12]=(u8)current->index;resource[0x49]=(u8)current->mask;D_800BE9C0=(u8)current->page;traceHash=2166136261u;
        v=(u32)func_1513B83C((Gfx *)commands,resource,(s16)current->view);
        h=hash(2166136261u,resource,8192);h=hash(h,commands,256);h=hash(h,&D_800BE9C0,1);
        if(h!=current->hash||traceHash!=current->trace||v!=current->value)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
LINK_FLAGS=['-Wl,--section-start=.resource=0x50000,--section-start=.commands=0x60000']
