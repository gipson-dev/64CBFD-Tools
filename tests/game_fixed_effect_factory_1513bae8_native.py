"""Native32 SDK fields; private frame payload mutations remain guest-only."""
from functools import lru_cache
import itertools
from tools.experiments import game_fixed_effect_factory_1513bae8_candidates as c
from tools.tests import game_fixed_effect_factory_1513bae8_oracle as g
def cases():
    for outcome,offset,mutation,seed in itertools.product((0,1),(0x1180,0,0x1181,0xFFFFFFFF,0x80000000),(0,2),range(5)):
        yield g.Case(outcome=outcome,offset=offset,mutation=mutation,seed=seed)
def digest(values):
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xFFFFFFFF
    return h
@lru_cache(None)
def rows():
    values=[]
    for case in cases():
        e=g.reference(g.fixture(case,'little'),case,order='little');trace=[]
        for t,args in e['calls']:
            args=list(args)
            if t==g.CREATE:args[0]=0xEEEEEEEE
            if t==g.FREE:args[0]=g.OUTPUT
            if t==g.COPY:args[0]=g.OUTPUT+0x1278;args[1]=0xDDDDDDDD
            for v in(t,len(args),*args):trace.extend(g.u32(v).to_bytes(4,'little'))
            if t==g.CREATE:trace.extend(e['packets'][0][1][i]for i in g.DEFINED)
            if t==g.COPY:trace.extend(next(p[2]for p in e['packets']if p[0]==g.COPY))
        h=digest(g.data(e['memory'],g.OUTPUT-64,8192))
        values.append('{%s}'%','.join('0x%Xu'%g.u32(v)for v in(case.outcome,case.offset,case.mutation,case.seed,h,digest(trace),g.OUTPUT if case.outcome else 0)))
    return ',\n'.join(values)
def harness(body=None):
    fields=','.join('{%d,%d,0x%Xu}'%(o,n,v)for o,n,v in g.FIELDS)
    defined=','.join(map(str,g.DEFINED))
    return '#include <ultra64.h>\n#include "structs.h"\n'+c.SUPPORT+'''
s32 func_1513B5E0(EffectDescriptor1513BAE8 *,u8,s32,u8,s32);
void func_1516972C(struct102 *);
void *memcpy(void *,const void *,u32);
'''+(c.SELECTED if body is None else body)+r'''
typedef char DescriptorSize[sizeof(EffectDescriptor1513BAE8)==60?1:-1];
typedef char PayloadSize[sizeof(EffectPayload1513BAE8)==20?1:-1];
typedef char Descriptor30[__builtin_offsetof(EffectDescriptor1513BAE8,field30)==48?1:-1];
typedef char Descriptor38[__builtin_offsetof(EffectDescriptor1513BAE8,field38)==56?1:-1];
typedef struct{u32 outcome,offset,mutation,seed,hash,trace,value;}Case;
static const Case cases[]={
'''+rows()+r'''};
static const u32 fields[][3]={'''+fields+r'''};
static const u8 defined[]={'''+defined+r'''};
static u32 arena[2048];static u8 *output=(u8 *)arena+64;static const Case *current;static u32 traceHash,bad;
static void bytehash(u8 b){traceHash=(traceHash^b)*16777619u;}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){bytehash((u8)v);v>>=8;}}
static void begin(u32 t,u32 n){mix(t);mix(n);}
static void wr(u8 *p,u32 v,u32 n){u32 i;for(i=0;i<n;i++){p[i]=(u8)v;v>>=8;}}
static u32 rd(const u8 *p,u32 n){u32 i,v=0;for(i=0;i<n;i++)v|=(u32)p[i]<<(8*i);return v;}
s32 func_1513B5E0(EffectDescriptor1513BAE8 *descriptor,u8 mode,s32 size,u8 priority,s32 context){
    u32 i;u8 *p=(u8 *)descriptor;begin(0x1513B5E0,5);mix(0xEEEEEEEE);mix(mode);mix((u32)size);mix(priority);mix((u32)context);
    for(i=0;i<sizeof(defined);i++)bytehash(p[defined[i]]);
    for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){if(rd(p+fields[i][0],fields[i][1])!=fields[i][2])bad=1;if(current->mutation&2)wr(p+fields[i][0],fields[i][2]^0x55,fields[i][1]);}
    if(!current->outcome)return 0;wr(output+0x50,current->offset,4);return(s32)(u32)output;
}
void func_1516972C(struct102 *object){begin(0x1516972C,1);mix((u8 *)object==output?0x60000:0);if((u8 *)object!=output)bad=1;}
void *memcpy(void *dest,const void *src,u32 n){
    u8 *d=dest;const u8 *s=src;u32 i;begin(0x10022EC0,3);mix(d==output+0x1278?0x61278:0);mix(0xDDDDDDDD);mix(n);
    if(d!=output+0x1278||n>32)bad=1;for(i=0;i<n;i++)bytehash(s[i]);for(i=0;i<n;i++)d[i]=s[i];return dest;
}
static int run(void){u32 i,j,h,value;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
    current=&cases[i];for(j=0;j<sizeof(arena);j++)((u8 *)arena)[j]=(u8)(j*29+current->seed*11+90);for(j=0;j<4;j++)output[0x50+j]=0xA5;
    traceHash=2166136261u;bad=0;value=(u32)func_1513BAE8();value=value==(u32)output?0x60000:value;
    h=2166136261u;for(j=0;j<sizeof(arena);j++)h=(h^((u8 *)arena)[j])*16777619u;
    if(bad||h!=current->hash||traceHash!=current->trace||value!=current->value)return 1;
}return 0;}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
