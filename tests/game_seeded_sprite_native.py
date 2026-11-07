"""Native32 caller fixtures from an independent little-endian byte model."""
import itertools
from unittest.mock import patch
from tools.experiments import game_seeded_sprite_candidates as c
from tools.tests import game_seeded_sprite_oracle as g
REGIONS=((g.ACTOR-32,576),(g.OTHER-32,576),(g.OUTPUT-32,320),(g.HEADER,32),(g.SENTINEL,4),(g.SEED,8))
def read(m,p,n=4):return int.from_bytes(bytes(m[p+i]for i in range(n)),'little')
def put(m,p,v,n=4):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,'little')):m[p+i]=b
def digest(values):
    h=2166136261
    for v in values:h=((h^(v&255))*16777619)&0xFFFFFFFF
    return h
def trace(calls,packets):
    values=[];pi=0
    for t,a in calls:
        aa=list(a)
        if t in(g.ZERO,g.INITIALIZE,g.CREATE):aa[0]=0xEEEEEEEE
        for v in(t,len(aa),*aa):values.extend((v&0xFFFFFFFF).to_bytes(4,'little'))
        if t==g.CREATE:values.extend(packets[pi]);pi+=1
    return digest(values)
def cases():
    for height,y,mutation,outcome,alias in itertools.product((-32768,-10000,-9999,32767),(-32768,0,32767),(0,1,2,4,8,15),(0,1),(0,1,2,3)):
        yield g.Case(height=height,y=y,mutation=mutation,outcome=outcome,alias=alias,random=((height*1664525+y*1013904223)&0xFFFFFFFF),width=(height+y)&65535,tall=(height-y)&65535)
def harness(body=None):
    rows=[]
    with patch.object(g,'read',read),patch.object(g,'put',put),patch.object(g.sprite,'read',read),patch.object(g.sprite,'put',put):
        for case in cases():
            e=g.reference(g.fixture(case),case);h=digest(e['memory'][p+i]for p,n in REGIONS for i in range(n));th=trace(e['calls'],e['packets'])
            rows.append('{%d,%d,%d,%d,%d,0x%Xu,%d,%d,%d,%d,%d,0x%Xu,0x%Xu}'%(case.x,case.y,case.z,case.height,case.variant,case.random,case.mutation,case.outcome,case.alias,case.width,case.tall,h,th))
    return '#include <ultra64.h>\n'+c.SUPPORT+'\nf32 D_800A81B0;\n'+(c.SELECTED if body is None else body)+r'''
typedef char CheckSize[sizeof(SeedSpriteDescriptor)==168?1:-1];
typedef char CheckHeight[__builtin_offsetof(SeedSpriteDescriptor,height)==0x96?1:-1];
typedef char CheckPosition[__builtin_offsetof(SeedSpriteDescriptor,x)==0x8C?1:-1];
typedef struct{s32 x,y,z,height,variant;u32 random;u32 mutation,outcome,alias,width,tall,publicHash,traceHash;} Case;
static const Case cases[]={
'''+',\n'.join(rows)+r'''};
static u32 arenaA[144],arenaB[144],arenaOut[80],header[8];
static u64 seed;
static u8 *actor=(u8 *)arenaA+32,*other=(u8 *)arenaB+32,*output=(u8 *)arenaOut+32;
static const Case *current;
static u32 traceHash;
static void bytehash(u8 b){traceHash=(traceHash^b)*16777619u;}
static void mix(u32 x){u32 i;for(i=0;i<4;i++){bytehash((u8)x);x>>=8;}}
static void begin(u32 target,u32 n){mix(target);mix(n);}
static u32 get16(u8 *p){return (u32)p[0]|(u32)p[1]<<8;}
static void put16(u8 *p,u32 x){p[0]=(u8)x;p[1]=(u8)(x>>8);}
static void effect(u32 stage){u32 mode=current->mutation;
 if(stage==0&&(mode&1)){put16(actor+0x28,32767);put16(actor+0x2A,(u32)-32768);put16(actor+0x2C,(u32)-32768);put16(actor+0x2E,(u32)-10000);actor[0x30]=255;}
 if(stage==1&&(mode&2)){actor[0xC]=33;actor[1]=222;other[0xC]=44;other[1]=199;}
 if(stage==2&&(mode&4)){put16(actor+0xE,(u32)-123);actor[0x30]=0xA7;}
 if(stage==3&&(mode&8)){put16(actor+0xE,(u32)-32768);actor[0x30]=0x5A;}
}
void bzero(void *dest,int len){u32 i;begin(0x100226F0,2);mix(0xEEEEEEEE);mix((u32)len);for(i=0;i<(u32)len;i++)((u8 *)dest)[i]=0;effect(0);}
void func_1516865C(void *dest,u8 red,u8 green,u8 blue,u8 alpha){u8 *p=dest;u32 i,flags=get16(p+0x98);s16 highU=(s16)((current->width+256)*32),highV=(s16)((current->tall+256)*32),lowU=8192,lowV=8192;begin(0x1516865C,5);mix(0xEEEEEEEE);mix(red);mix(green);mix(blue);mix(alpha);
 for(i=0;i<8;i++){put16(p+16*i+6,0);p[16*i+12]=red;p[16*i+13]=green;p[16*i+14]=blue;p[16*i+15]=alpha;}
 if(flags&128){highV=8192;lowV=(s16)((current->tall+256)*32);}if(flags&256){highU=8192;lowU=(s16)((current->width+256)*32);}
 for(i=0;i<8;i++){u32 corner=i&3;put16(p+16*i+8,(u16)((corner==0||corner==3)?highU:lowU));put16(p+16*i+10,(u16)(corner<2?highV:lowV));}
 put16(p+0x88,0);put16(p+0x9C,0);put16(p+0x9E,0);effect(1);
}
void *func_15168800(void *source,u8 priority,s32 owner){u32 i;u8 *dest=current->alias==1?actor-16:current->alias==2?actor:current->alias==3?other-16:output;begin(0x15168800,3);mix(0xEEEEEEEE);mix(priority);mix((u32)owner);for(i=0;i<168;i++)bytehash(((u8 *)source)[i]);effect(2);if(!current->outcome)return 0;for(i=0;i<168;i++)dest[16+i]=((u8 *)source)[i];return dest;}
s32 func_150ADA20(void){begin(0x150ADA20,0);effect(3);return (s32)current->random;}
static void initialize(const Case *c){u32 i,j;u8 *areas[4]={(u8 *)arenaA,(u8 *)arenaB,(u8 *)arenaOut,(u8 *)header};u32 sizes[4]={576,576,320,32};
 for(j=0;j<4;j++)for(i=0;i<sizes[j];i++)areas[j][i]=(u8)(i*29+90);
 put16(actor+0x28,(u32)c->x);put16(actor+0x2A,(u32)c->y);put16(actor+0x2C,(u32)c->z);put16(actor+0x2E,(u32)c->height);actor[0x30]=(u8)c->variant;actor[0xC]=0x83;actor[1]=0xC1;put16(actor+0xE,(u32)-1);actor[0xD]=0;actor[0x10]=1;actor[0x11]=255;
 put16(other+0x28,(u32)-32768);put16(other+0x2A,32767);put16(other+0x2C,41);put16(other+0x2E,123);other[0x30]=0x33;other[0xC]=0x45;other[1]=0xEF;put16(other+0xE,(u32)-1);
 put16((u8 *)header+6,c->width);put16((u8 *)header+8,c->tall);D_800A81B0=-10000.0f;seed=1;traceHash=2166136261u;
}
static u32 public_hash(void){u32 h=2166136261u,i,j;u8 *areas[6]={(u8 *)arenaA,(u8 *)arenaB,(u8 *)arenaOut,(u8 *)header,(u8 *)&D_800A81B0,(u8 *)&seed};u32 sizes[6]={576,576,320,32,4,8};for(j=0;j<6;j++)for(i=0;i<sizes[j];i++)h=(h^areas[j][i])*16777619u;return h;}
static int run(void){u32 i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;initialize(current);func_15193390(actor);if(traceHash!=current->traceHash)return 11;if(public_hash()!=current->publicHash)return 12;}return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
