"""SDK native32 checks for finite ordinary records and typed callback tables."""
from functools import lru_cache
from tools.experiments import game_dual_record_animation_update_1513cfe4_candidates as c
from tools.tests import game_dual_record_animation_update_1513cfe4_oracle as g

REGIONS=((g.RESOURCE,256),(g.FOLLOW,256),(g.FRAMES,3072),(g.TICKS-32,192),(g.MARK,16))
FIELDS=('enabled','flags','timer','threshold','scale','alpha','animation','frames','cursor','rate','ticks','update','second','second_answer','exit','answer','exit_answer','mutation','seed')
def cases():
    return tuple(v for v in g.cases()if v.alias==0 and v.mutation not in(2,4)and v.animation<30 and v.ticks<=65535 and g.reference(g.fixture(v),v)['status']=='return')
def digest(values):
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xFFFFFFFF
    return h
def trace(calls):return b''.join(g.u32(v).to_bytes(4,'little')for t,a in calls for v in(t,len(a),*a))
@lru_cache(None)
def rows():
    rows=[]
    for case in cases():
        e=g.reference(g.fixture(case,'little'),case,'little');observed=b''.join(g.ram.data(e['memory'],a,n)for a,n in REGIONS)
        values=[g.u32(getattr(case,k))for k in FIELDS]+[digest(observed),digest(trace(e['calls']))]
        rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(rows)

def harness(body=None):
    updates,second,exits,frames=g.retained()
    target_literals=lambda vs:','.join('0x%Xu'%v for v in vs)
    funcs=[];arrays=[]
    for name,vs,section,stage in(('D_80089CB8',updates,'updates',0),('D_80089D60',second,'second',1),('D_80089E10',exits,'exits',2)):
        funcs.extend('static s32 cb%d_%d(u8 *p){return provider(%d,0x%X,p);}'%(stage,i,stage,t)for i,t in enumerate(vs)if i)
        arrays.append('s32 (*%s[%d])(u8 *) __attribute__((section(".%s"),used,aligned(4)))={0,'% (name,len(vs),section)+','.join('cb%d_%d'%(stage,i)for i in range(1,len(vs)))+'};')
    update_funcs='\n'.join(funcs);exit_funcs='';arrays='\n'.join(arrays)
    return '#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\nextern u8 D_80090B64[];\n'+c.DECLARATIONS+'\n'+(c.SELECTED if body is None else body)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef struct{u32 enabled,flags,timer,threshold,scale,alpha,animation,frames,cursor,rate,ticks,update,second,second_answer,exit,answer,exit_answer,mutation,seed,hash,trace;}Case;
static const Case cases[]={
'''+rows()+r'''};
static const u8 retainedFrames[]={'''+','.join(str(v)for v in frames)+r'''};
static u8 resource[256] __attribute__((section(".resource"),used,aligned(8)));
static u8 follow[256] __attribute__((section(".follow"),used,aligned(8)));
static u8 marker[16] __attribute__((section(".marker"),used,aligned(8)));
u8 D_80090B64[3072] __attribute__((section(".frames"),used,aligned(4)));
static u32 timing[48] __attribute__((section(".timing"),used,aligned(4)));
__asm__(".globl D_800BE9E4\n.set D_800BE9E4,timing+32\n");
static const Case *current;static u32 traceHash;
static void wr(u8 *p,u32 v,u32 n){u32 i;for(i=0;i<n;i++){p[i]=(u8)v;v>>=8;}}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
static s32 provider(u32 stage,u32 t,u8 *record){
    mix(t);mix(1);mix((u32)record);
    if(stage==3){wr(marker,(u32)record,4);return 0;}
    if(stage==2)return(s32)current->exit_answer;
    if(current->mutation==1){wr(record+0x58,0x18000000,4);wr(record+0x1C,(u32)-3,2);wr(record+0x6E,7,2);D_800BE9E4=3;}
    if(current->mutation==3){wr(record+0x20,131071,4);wr(record+0x24,1,4);D_80090B64[record[0x18]*12]=1;}
    if(current->mutation==5&&stage==0){record[0x71]=2;record[0x72]=2;}
    if(current->mutation==6&&stage==1)wr(record+0x58,0x18000000,4);
    return(s32)(stage==0?current->answer:current->second_answer);
}
'''+update_funcs+'\n'+exit_funcs+'\n'+arrays+r'''
void func_1516972C(struct102 *p){(void)provider(3,0x1516972C,(u8 *)p);}
static int run(void){u8 *p[5]={resource,follow,D_80090B64,(u8 *)timing,marker};u32 n[5]={256,256,3072,192,16};u32 i,j,k,h;void(*callback)(u8 *)=func_1513CFE4;
    if((u32)resource!=0x30000||(u32)follow!=0x50000||(u32)marker!=0x60000||(u32)D_80090B64!=0x80090B64||(u32)&D_800BE9E4!=0x800BE9E4||(u32)D_80089CB8!=0x80089CB8||(u32)D_80089D60!=0x80089D60||(u32)D_80089E10!=0x80089E10)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];for(k=0;k<5;k++)for(j=0;j<n[k];j++)p[k][j]=(u8)(j*29+current->seed*11+90);
        for(j=0;j<3072;j++)D_80090B64[j]=retainedFrames[j];D_800BE9E4=(s32)current->ticks;
        for(k=0;k<2;k++){
            u8 *r=p[k];wr(r+0x10,current->enabled,4);wr(r+0x58,current->flags,4);wr(r+0x20,current->cursor,4);wr(r+0x24,current->rate,4);
            wr(r+0x1C,current->timer,2);wr(r+0x6C,current->threshold,2);wr(r+0x6E,current->scale,2);
            r[0x18]=(u8)current->animation;r[0x5C]=(u8)current->alpha;r[0x2B]=91;r[0x70]=(u8)current->update;r[0x71]=(u8)current->second;r[0x72]=(u8)current->exit;
        }
        D_80090B64[current->animation*12]=(u8)current->frames;traceHash=2166136261u;callback(resource);h=2166136261u;
        for(k=0;k<5;k++)for(j=0;j<n[k];j++)h=(h^p[k][j])*16777619u;
        if(h!=current->hash||traceHash!=current->trace)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.resource=0x30000,--section-start=.follow=0x50000,--section-start=.marker=0x60000,--section-start=.frames=0x80090B64,--section-start=.timing=0x800BE9C4,--section-start=.updates=0x80089CB8,--section-start=.second=0x80089D60,--section-start=.exits=0x80089E10']
