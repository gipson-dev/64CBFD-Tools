"""Freestanding native32 SDK body with fixed disjoint arenas and independent hashes."""
from functools import lru_cache
import itertools
from tools.experiments import game_resource_view_creator_1513b5e0_candidates as c
from tools.tests import game_resource_view_creator_1513b5e0_oracle as g

def cases():
    for outcome,views,extent,seed in itertools.product((0,1),(-1,0,1,2),(0,4,64,1120),range(2)):
        yield g.Case(outcome=outcome,views=views,extent=extent,seed=seed)
    for mutation in range(1,7):yield g.Case(mutation=mutation,views=2)
    for mode,priority,extra,context in((0,0,0,0),(0x100,0x100,0xFFFFFFFF,0x80000000),(0xFFFFFFFF,0xFFFF0081,0x7FFFFFFF,0xFFFFFFFF)):
        yield g.Case(mode=mode,priority=priority,extra=extra,context=context)
    for views in(0x7FFFFFFF,0x80000000):yield g.Case(views=views)

def digest(values):
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xFFFFFFFF
    return h
@lru_cache(None)
def rows():
    rows=[]
    for case in cases():
        e=g.reference(g.fixture(case,'little'),case,'little');trace=[]
        for t,a in e['calls']:
            a=list(a)
            if t==g.RESOLVE:a[0]=0xEEEE0001;a[2]=0xEEEE0003
            for v in(t,len(a),*a):trace.extend(g.u32(v).to_bytes(4,'little'))
        memory=[]
        for a,n in g.REGIONS:memory.extend(g.data(e['memory'],a,n))
        memory.extend(g.data(e['memory'],g.VIEWS,4))
        values=(case.outcome,case.mode,case.priority,case.extra,case.context,case.views,case.extent,case.mutation,case.seed,digest(memory),digest(trace),e['value'])
        rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}')
    return ',\n'.join(rows)

def harness(body=None):
    return '#include <ultra64.h>\n'+c.SUPPORT+'\n'+c.DECLARATIONS+'''
void *memcpy(void *,const void *,u32);
extern s32 D_80082FA0;
'''+(c.SELECTED if body is None else body)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef char DescriptorSize[sizeof(EffectDescriptor1513BAE8)==60?1:-1];
typedef char Descriptor30[__builtin_offsetof(EffectDescriptor1513BAE8,field30)==48?1:-1];
typedef char Descriptor34[__builtin_offsetof(EffectDescriptor1513BAE8,field34)==52?1:-1];
typedef struct {u32 outcome,mode,priority,extra,context,views,extent,mutation,seed,hash,trace,value;}Case;
static const Case cases[]={
'''+rows()+r'''};
static u32 outputWords[4096] __attribute__((section(".output"),aligned(4)));
static u32 assetWords[2048] __attribute__((section(".asset"),aligned(4)));
static u32 descriptorWords[32] __attribute__((section(".descriptor"),aligned(4)));
static u32 alternateWords[1024] __attribute__((section(".alternate"),aligned(4)));
static u8 *output=(u8 *)outputWords,*asset=(u8 *)assetWords,*descriptor=(u8 *)descriptorWords,*alternate=(u8 *)alternateWords;
s32 D_80082FA0;
static const Case *current;static u32 traceHash,copies,bad;
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
static void begin(u32 t,u32 n){mix(t);mix(n);}
static void wr(u8 *p,u32 v){u32 i;for(i=0;i<4;i++){p[i]=(u8)v;v>>=8;}}
static void effect(u32 t){
    u32 m=current->mutation;
    if(m==1&&t==0x1502B6BC){wr(descriptor+48,0x11223344);wr(descriptor+52,0x55667788);}
    if((m==2&&t==0x15167A68)||(m==3&&t==0x10022EC0&&copies==1))D_80082FA0=1;
    if(m==4&&t==0x10022EC0&&copies==2){wr(output+0x68,(u32)alternate);wr(asset,(u32)asset+44+current->extent);}
    if(m==5&&t==0x10022EC0&&copies==3)D_80082FA0=0;
    if(m==6&&t==0x1510CE60)wr(output+0x50,0xFEED1234);
}
void *func_1502B6BC(s32 *size,s32 zero,s32 *status,s32 mode,...){
    __builtin_va_list ap;s32 first,second;__builtin_va_start(ap,mode);first=__builtin_va_arg(ap,s32);second=__builtin_va_arg(ap,s32);__builtin_va_end(ap);
    begin(0x1502B6BC,6);mix(0xEEEE0001);mix((u32)zero);mix(0xEEEE0003);mix((u32)mode);mix((u32)first);mix((u32)second);
    if(!size||!status)bad=1;*size=0x12345678;*status=(s32)0x87654321u;effect(0x1502B6BC);return asset;
}
void *func_15167A68(s32 kind,s32 context,s32 size,s32 group,u8 priority,u8 one){
    begin(0x15167A68,6);mix((u32)kind);mix((u32)context);mix((u32)size);mix((u32)group);mix(priority);mix(one);effect(0x15167A68);return current->outcome?output:0;
}
void *memcpy(void *dest,const void *src,u32 n){
    u8 *d=dest;const u8 *s=src;u32 i;begin(0x10022EC0,3);mix((u32)d);mix((u32)s);mix(n);copies++;
    if(n>2240)bad=1;for(i=0;i<n;i++)d[i]=s[i];effect(0x10022EC0);return dest;
}
s32 func_1510CE60(void *end,s32 zero,s32 one,s32 command,s32 *unused){
    begin(0x1510CE60,5);mix((u32)end);mix((u32)zero);mix((u32)one);mix((u32)command);mix((u32)unused);effect(0x1510CE60);return 0x76543210;
}
static u32 hash(u32 h,u8 *p,u32 n){u32 i;for(i=0;i<n;i++)h=(h^p[i])*16777619u;return h;}
static int run(void){u32 i,j,k,h,v;u8 *p[4]={output,asset,descriptor,alternate};u32 n[4]={16384,8192,128,4096};
    if((u32)output!=0x60000||(u32)asset!=0x80000||(u32)descriptor!=0xA0000||(u32)alternate!=0xC0000)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];for(k=0;k<4;k++)for(j=0;j<n[k];j++)p[k][j]=(u8)(j*29+current->seed*11+90);
        wr(asset,(u32)asset+40+current->extent);D_80082FA0=(s32)current->views;traceHash=2166136261u;copies=bad=0;
        v=(u32)func_1513B5E0((EffectDescriptor1513BAE8 *)descriptor,(u8)current->mode,(s32)current->extra,(u8)current->priority,(s32)current->context);
        h=2166136261u;for(k=0;k<4;k++)h=hash(h,p[k],n[k]);h=hash(h,(u8 *)&D_80082FA0,4);
        if(bad||h!=current->hash||traceHash!=current->trace||v!=current->value)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.output=0x60000,--section-start=.asset=0x80000,--section-start=.descriptor=0xA0000,--section-start=.alternate=0xC0000']
