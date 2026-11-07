"""Independent little-endian native fixtures; implicit padding is not compared."""
from functools import lru_cache
import itertools
from tools.experiments import game_position_payload_candidates as c
from tools.tests import game_position_payload_oracle as g
PADDING=(5,6,7,53,54,55)
REGIONS=((g.ACTOR-64,768),(g.OUTPUT-64,384),(g.DEFAULT,12))
def digest(values):
    h=2166136261
    for v in values:h=((h^(v&255))*16777619)&0xFFFFFFFF
    return h
def cases():
    for selector in range(256):yield g.Case(selector=selector,priority=255-selector,identity=selector)
    for result,vector,default,mutation,outcome,alias in itertools.product((0,1,0xFFFFFFFF),(0,2),(0,1),(0,1,2,8,3,11),(0,1),(0,1,3)):
        yield g.Case(result=result,vector=vector,default=default,mutation=mutation,outcome=outcome,alias=alias,priority=0x80,context=0x80000000)
def hashes(case):
    initial=g.fixture(case,order='little');e=g.reference(initial,case,order='little');m=e['memory'];dest=g.destination(case,g.STACK)+40 if case.outcome else None;values=[]
    for base,n in REGIONS:
        for i in range(n):
            p=base+i
            if dest is not None and p-dest in PADDING:continue
            values.append(m[p])
    trace=[];pi=0
    for t,args in e['calls']:
        args=list(args)
        if t==g.FAKE:args[1]=0xEEEEEEEE
        elif t==g.COPY:args[0]=0xDDDDDDDD;args[1]=0xCCCCCCCC
        for v in(t,len(args),*args):trace.extend(g.u32(v).to_bytes(4,'little'))
        if t==g.COPY:
            packet=[p for target,p in e['packets']if target==g.COPY][pi];pi+=1
            trace.extend(b for i,b in enumerate(packet)if i not in PADDING)
    return digest(values),digest(trace)
@lru_cache(None)
def fixture_rows():
    rows=[]
    for case in cases():
        h,t=hashes(case);rows.append('{%d,%d,0x%Xu,%d,0x%Xu,%d,%d,%d,%d,%d,0x%Xu,0x%Xu}'%(case.selector,case.priority,g.u32(case.context),case.identity,g.u32(case.result),case.vector,case.default,case.mutation,case.outcome,case.alias,h,t))
    return rows
def harness(body=None):
    declarations='void *func_15149130(s16,s8,s8,s8,u8,u8,s32,u8,s32);\nvoid *memcpy(void *,const void *,u32);\n'
    callback_support='''typedef struct {s32 a,b,c;} ThreeWord1FA770;
ThreeWord1FA770 D_800AAF9C[2]={{0x3F800000,(s32)0xC0000000,0x40400000},{0x40800000,0x40A00000,0x40C00000}};
void func_15143134(void *,void *,void *);
s32 func_151D10E4(u8 *,void *,u8);
'''
    callbacks='\n'.join(new for old,new in c.REPAIRS[1:])
    expected_y=','.join('0x%Xu'%g.bits(g.floating(v[1])+8.0)for v in g.VECTORS)
    return '#include <ultra64.h>\n'+c.SUPPORT+declarations+callback_support+callbacks+'\n'+(c.SELECTED if body is None else body)+r'''
typedef char PayloadSize[sizeof(PositionPayload151D0F60)==56?1:-1];
typedef char CallbackOutputOffset[__builtin_offsetof(PositionPayload151D0F60,second)==24?1:-1];
typedef char SelectorOffset[__builtin_offsetof(PositionPayload151D0F60,selector)==52?1:-1];
typedef struct {u32 selector,priority,context,identity,result,vector,defaultKind,mutation,outcome,alias,hash,trace;} Case;
static const Case cases[]={
'''+',\n'.join(fixture_rows())+r'''};
PositionVector151D0F60 D_800A5480;
static s32 positionCallback(u8 *,PositionVector151D0F60 *);
s32 (*D_8008FC30[256])(u8 *,PositionVector151D0F60 *);
static u32 actorArena[192],outputArena[96];
static u8 *actor=(u8 *)actorArena+64,*output=(u8 *)outputArena+64,*copied;
static const Case *current;static u32 traceHash,bad;
static const u32 vectors[3][3]={{0x3F800000,0xC0200000,0x42C60000},{0xC7000000,0x3E800000,0x46FFFE00},{0x80000000,0,0xBF800000}};
static const u32 defaults[2][3]={{0,0,0},{0x41200000,0xC1A00000,0x41F00000}};
static u32 padding(u32 i){return i==5||i==6||i==7||i==53||i==54||i==55;}
static void bytehash(u8 b){traceHash=(traceHash^b)*16777619u;}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){bytehash((u8)v);v>>=8;}}
static void begin(u32 t,u32 n){mix(t);mix(n);}
static void setDefault(const u32 *v){u32 i;for(i=0;i<3;i++)((u32 *)&D_800A5480)[i]=v[i];}
static s32 positionCallback(u8 *p,PositionVector151D0F60 *v){u32 i;begin(0x17001000,2);mix(p==actor?0x30000:0);mix(0xEEEEEEEE);for(i=0;i<3;i++)((u32 *)v)[i]=vectors[current->vector][i];if(current->mutation&1)p[0x3B]^=0x55;if(current->mutation&2)setDefault(vectors[1]);return (s32)current->result;}
void *func_15149130(s16 life,s8 a,s8 b,s8 d,u8 flags,u8 kind,s32 size,u8 priority,s32 context){u32 i;u8 *p=current->alias==1?actor-40:current->alias==3?actor:output;
 begin(0x15149130,9);mix((u32)life);mix((u32)a);mix((u32)b);mix((u32)d);mix(flags);mix(kind);mix((u32)size);mix(priority);mix((u32)context);
 if(current->mutation&8){actor[0x3B]^=0xAA;setDefault(vectors[2]);}
 if(!current->outcome)return 0;
 *(u16 *)(p+14)=(u16)life;p[16]=(u8)a;p[17]=(u8)b;p[18]=(u8)d;p[13]=flags;p[19]=kind;for(i=0;i<16;i++)p[20+i]=0;return p;
}
void *memcpy(void *dest,const void *src,u32 n){u32 i;u8 *d=dest;const u8 *s=src;begin(0x10022EC0,3);mix(0xDDDDDDDD);mix(0xCCCCCCCC);mix(n);if(*(u8 *const *)src!=actor)bad=1;
 for(i=0;i<n;i++)if(!padding(i))bytehash(i<4?(u8)(0x30000u>>(i*8)):s[i]);
 for(i=0;i<n;i++)d[i]=s[i];copied=d;return dest;
}
static void fill(void *p,u32 n){u32 i;for(i=0;i<n;i++)((u8 *)p)[i]=(u8)(i*29+90);}
static void initialize(void){u32 i;fill(actorArena,sizeof(actorArena));fill(outputArena,sizeof(outputArena));actor[0x3B]=(u8)current->identity;*(u32 *)(actor+0x14)=vectors[current->vector][0];*(u32 *)(actor+0x180)=vectors[current->vector][1];*(u32 *)(actor+0x1C)=vectors[current->vector][2];*(u32 *)(actor+0x1D4)=0x90000;setDefault(defaults[current->defaultKind]);for(i=0;i<256;i++)D_8008FC30[i]=positionCallback;traceHash=2166136261u;copied=0;bad=0;}
static u32 publicHash(void){u32 i,j,offset,h=2166136261u;u8 *areas[3]={(u8 *)actorArena,(u8 *)outputArena,(u8 *)&D_800A5480};u32 sizes[3]={768,384,12};
 for(j=0;j<3;j++)for(i=0;i<sizes[j];i++){u8 *p=areas[j]+i,value=*p;u32 address=(u32)p,base=(u32)copied;if(copied&&address>=base&&address-base<56){offset=address-base;if(padding(offset))continue;if(offset<4)value=(u8)(0x30000u>>(offset*8));}h=(h^value)*16777619u;}return h;
}
static s32 (*const actualCallbacks[3])(u8 *,PositionVector151D0F60 *)={func_151D1074,func_151D10A4,func_151D10C4};
static u32 transformRow;
void func_15143134(void *row,void *dest,void *matrix){u32 i;transformRow=row==&D_800AAF9C[1]?1:0;if(matrix!=(void *)0x90000)bad=1;for(i=0;i<3;i++)((u32 *)dest)[i]=((u32 *)row)[i];}
static int checkCallbacks(void){u32 vector,selector,matrix,i,out[3];s32 result;static const u32 expectedY[]={'''+expected_y+r'''};
 for(vector=0;vector<3;vector++)for(selector=0;selector<3;selector++)for(matrix=0;matrix<2;matrix++){
  *(u32 *)(actor+0x14)=vectors[vector][0];*(u32 *)(actor+0x180)=vectors[vector][1];*(u32 *)(actor+0x1C)=vectors[vector][2];*(u32 *)(actor+0x1D4)=matrix?0x90000:0;
  for(i=0;i<3;i++)out[i]=0x12340000u+i;transformRow=99;result=actualCallbacks[selector](actor,(PositionVector151D0F60 *)out);
  if(result!=(s32)(selector==0||matrix))return 21;
  if(selector==0){if(out[0]!=vectors[vector][0]||out[1]!=expectedY[vector]||out[2]!=vectors[vector][2])return 22;}
  else if(matrix){if(bad||transformRow!=selector-1)return 23;for(i=0;i<3;i++)if(out[i]!=((u32 *)&D_800AAF9C[selector-1])[i])return 24;}
  else for(i=0;i<3;i++)if(out[i]!=0x12340000u+i)return 25;
 }return 0;
}
static int run(void){u32 i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=&cases[i];initialize();func_151D0F60(actor,(u8)current->selector,(u8)current->priority,(s32)current->context);if(bad||publicHash()!=current->hash)return 11;if(traceHash!=current->trace)return 12;}return checkCallbacks();}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
