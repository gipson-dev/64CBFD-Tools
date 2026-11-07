"""SDK native32 fixtures from an independent little-endian memory reference."""
import itertools
from functools import lru_cache
from tools.experiments import game_active_entry_reset_candidates as c
from tools.tests import game_active_entry_reset_oracle as g
def digest(values):
    h=2166136261
    for v in values:h=((h^(v&255))*16777619)&0xFFFFFFFF
    return h
def mix(values):return digest(b for v in values for b in g.u32(v).to_bytes(4,'little'))
def cases():
    for pattern,base,span,random in itertools.product(range(6),(-32768,32767),(-32768,-2,0,32767),(0,0xFFFFFFFF)):
        yield g.Case(pattern=pattern,base=base,span=span,random=random)
    for mutation in range(64):
        if not mutation&8:yield g.Case(pattern=5,mutation=mutation)
def hashes(case):
    initial=g.fixture(case,order='little');e=g.reference(initial,case,order='little');m=e['memory'];owner,entries,actors=g.addresses(case);values=[]
    for p,n in((*[(a,512)for a in actors],(owner,36),(g.TABLE,5120))):values.extend(m[p+i]for i in range(n))
    for i in range(60):
        value=g.rd(m,entries+i*12,order='little');identity=0 if value==0 else actors.index(value)+1
        values.extend(identity.to_bytes(4,'little'));values.extend(m[entries+i*12+4+k]for k in range(8))
    values.extend(m[g.ALTERNATE+i]for i in range(720));trace=[]
    for t,args in e['calls']:
        args=list(args)
        if t==g.CONFIG:args[0]=actors.index(args[0])+1
        elif t==g.ZERO:args[0]=0 if args[0]==entries else 1
        trace.extend((t,len(args),*args))
    return digest(values),mix(trace)
@lru_cache(None)
def fixture_rows():
    rows=[]
    for case in cases():
        h,t=hashes(case);rows.append('{%d,%d,%d,%d,0x%Xu,%d,0x%Xu,0x%Xu}'%(case.pattern,case.selector,case.base,case.span,case.random,case.mutation,h,t))
    return rows
def harness(body=None):
    return '#include <ultra64.h>\n#include "structs.h"\ns32 func_150ADA20(void);\n'+c.SUPPORT+'\n'+(c.SELECTED if body is None else body)+r'''
typedef char EntrySize[sizeof(ActiveResetEntry15191400)==12?1:-1];
typedef char PresetSize[sizeof(ActiveResetPreset15191400)==20?1:-1];
typedef char OwnerSize[sizeof(ActiveResetOwner15191400)==40?1:-1];
typedef char EntriesOffset[__builtin_offsetof(ActiveResetOwner15191400,entries)==0x24?1:-1];
typedef struct {s32 pattern,selector,base,span;u32 random,mutation,hash,trace;} Case;
static const Case cases[]={
'''+',\n'.join(fixture_rows())+r'''};
ActiveResetPreset15191400 D_800A9D40[256];
static u32 backing[4][128];
static ActiveResetEntry15191400 entries[60],alternate[60];
static ActiveResetOwner15191400 owner;
static const Case *current;
static u32 number,traceHash;
static u8 *actor(u32 i){return (u8 *)backing[i];}
static u32 identity(u8 *p){u32 i;if(!p)return 0;for(i=0;i<4;i++)if(p==actor(i))return i+1;return 99;}
static void bytehash(u8 x){traceHash=(traceHash^x)*16777619u;}
static void mix(u32 x){u32 i;for(i=0;i<4;i++){bytehash((u8)x);x>>=8;}}
static void begin(u32 t,u32 n){mix(t);mix(n);}
static void effect(u32 stage,u8 *target){u32 m=current->mutation,first=current->pattern==2?59:0;
 if(number)return;
 if(stage==0){
  if(m&1)entries[first].actor=actor(1);
  if(m&2){D_800A9D40[current->selector].base=-32768;D_800A9D40[current->selector].range=32767;target[0x130]=255;}
  if(m&4)owner.entries=alternate;
 }else{
  if(m&16)entries[first].actor=actor(2);
  if(m&32){D_800A9D40[current->selector].base=32767;D_800A9D40[current->selector].range=0;}
 }
}
void func_1513F680(struct171 *p,u8 a,u8 b,u8 d,u8 e){u8 *q=(u8 *)p;begin(0x1513F680,5);mix(identity(q));mix(a);mix(b);mix(d);mix(e);q[0x70]=a;q[0x71]=b;q[0x72]=d;q[0x73]=e;effect(0,q);}
s32 func_150ADA20(void){u32 value;begin(0x150ADA20,0);effect(1,0);value=current->random+number*0x9E3779B9u;number++;return (s32)value;}
void bzero(void *p,int n){u32 i;begin(0x100226F0,2);mix(p==(void *)entries?0:p==(void *)alternate?1:99);mix((u32)n);for(i=0;i<(u32)n;i++)((u8 *)p)[i]=0;}
static void fill(void *p,u32 n){u32 i;for(i=0;i<n;i++)((u8 *)p)[i]=(u8)(i*29+90);}
static void initialize(void){u32 i,j,k;fill(&owner,sizeof(owner));fill(entries,sizeof(entries));fill(alternate,sizeof(alternate));fill(D_800A9D40,sizeof(D_800A9D40));
 for(i=0;i<256;i++){D_800A9D40[i].base=(s16)current->base;D_800A9D40[i].range=(s16)current->span;}
 for(i=0;i<60;i++){u32 yes=current->pattern==1?i==0:current->pattern==2?i==59:current->pattern==3?i%2==0:current->pattern==4?1:current->pattern==5?(i==0||i==3||i==59):0;entries[i].actor=yes?actor(current->pattern==5?0:i%4):0;}
 for(j=0;j<4;j++){fill(actor(j),512);for(k=0;k<3;k++)*(u32 *)(actor(j)+0x110+k*4)=0x3F800000u+(j+k)*0x10000u;*(u16 *)(actor(j)+0x1C)=(u16)(0x8123+j);*(u32 *)(actor(j)+0x58)=0xA5A50000u+j*2;actor(j)[0x130]=(u8)current->selector;}
 *(u32 *)&owner.value1C=0x80000000u;owner.state20=0x01234567;owner.entries=entries;number=0;traceHash=2166136261u;
}
static u32 publicHash(void){u32 h=2166136261u,i,j,k,value;u8 *p;
 for(j=0;j<4;j++)for(i=0;i<512;i++)h=(h^actor(j)[i])*16777619u;
 p=(u8 *)&owner;for(i=0;i<36;i++)h=(h^p[i])*16777619u;
 p=(u8 *)D_800A9D40;for(i=0;i<sizeof(D_800A9D40);i++)h=(h^p[i])*16777619u;
 for(i=0;i<60;i++){value=identity(entries[i].actor);for(k=0;k<4;k++){h=(h^(value&255))*16777619u;value>>=8;}for(k=0;k<8;k++)h=(h^entries[i].retained04[k])*16777619u;}
 p=(u8 *)alternate;for(i=0;i<sizeof(alternate);i++)h=(h^p[i])*16777619u;return h;
}
static int run(void){u32 i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=&cases[i];initialize();func_15191400(&owner);if(publicHash()!=current->hash)return 11;if(traceHash!=current->trace)return 12;}return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
