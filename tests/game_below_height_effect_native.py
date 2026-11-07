"""SDK native32 checked against byte-wise little-endian Python fixtures."""
from dataclasses import replace
import itertools
from unittest.mock import patch
from tools.experiments import game_below_height_effect_candidates as c
from tools.tests import game_below_height_effect_oracle as g
REGIONS=((g.ACTOR,512),(g.POSITIONS-2700,5500),(g.PAYLOAD,256),(g.OTHER,256),(g.THRESHOLD,8),(g.RESET,4))
def read(m,p,n=4):return int.from_bytes(bytes(m[p+i]for i in range(n)),'little')
def put(m,p,v,n=4):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,'little')):m[p+i]=b
def digest(values):
    result=2166136261
    for value in values:result=((result^(value&255))*16777619)&0xFFFFFFFF
    return result
def trace(calls,vectors):
    data=[];vi=0
    for t,args in calls:
        values=[t,len(args),*args]
        if t==g.SUBMIT:
            values[6]=0xEEEEEEEE;values.extend(vectors[vi]);vi+=1
        for value in values:data.extend((value&0xFFFFFFFF).to_bytes(4,'little'))
    return digest(data)
def cases():
    for index,height,y,random,mutation,alias in itertools.product((-128,0,127),(g.bits(1.),g.bits(17.75)),(g.bits(1.),g.bits(-3.)),(g.bits(.25),g.bits(.8)),(0,1,2,4,7),(0,2,3)):
        yield g.Case(index=index,height=height,y=y,random=random,mutation=mutation,alias=alias,selector=(index*17+129)&255)
    for threshold,mutation in itertools.product((g.dbits(.80000003),g.dbits(.79999999)),(0,2,4,6)):
        yield g.Case(random=g.bits(.8),threshold=threshold,mutation=mutation)
def harness(rom,body=None):
    rows=[]
    with patch.object(g,'read',read),patch.object(g,'put',put):
        for case in cases():
            initial=g.fixture(rom,case);e=g.reference(initial,case)
            public=digest(e['memory'][base+i]for base,n in REGIONS for i in range(n));calls=trace(e['calls'],e['vectors'])
            rows.append('{%d,0x%Xu,0x%Xu,0x%Xu,%d,%d,%d,0x%XULL,0x%Xu,0x%Xu}'%(case.index,case.height,case.y,case.random,case.selector,case.mutation,case.alias,case.threshold,public,calls))
    return '#include <ultra64.h>\n'+c.SUPPORT+'\nf64 D_800A73A8;\nf32 D_800A73B0;\n'+(c.SELECTED if body is None else body)+r'''
typedef struct {s32 index;u32 height,y,random,selector,mutation,alias;u64 threshold;u32 publicHash,traceHash;} Case;
static const Case cases[]={
'''+',\n'.join(rows)+r'''};
static u32 a[128],v[1375],p[64],q[64];
static u8 *actor=(u8 *)a,*positions=(u8 *)v+2700,*saved;
static const Case *current;
static u32 traceHash;
static void mix(u32 x){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(x&255))*16777619u;x>>=8;}}
static void store(u8 *p,u32 x){*(u32 *)p=x;}
static void begin(u32 target,u32 count){mix(target);mix(count);}
static void effect(u32 stage){u32 mode=current->mutation;
 if(stage==0&&(mode&1)){actor[0x2D]++;*(u8 **)(actor+0x94)=positions+80;*(u8 **)(actor+0x98)=(u8 *)q;store(saved+0x48,0x42250000u);D_800A73A8=.5;}
 if(stage==1&&(mode&2)){actor[0x2D]++;*(u8 **)(actor+0x94)=positions+160;*(u8 **)(actor+0x98)=(u8 *)q;store(saved,0xC0500000u);saved[0x1B]=0xF1;actor[0xC]=33;actor[1]=222;store(saved+0x48,0xC2B70000u);}
 if(stage==2&&(mode&4)){*(u8 **)(actor+0x98)=(u8 *)q;saved[0x20]=0xAA;*(u32 *)&D_800A73B0=0x42C78000u;}
}
f32 func_150ADA68(void){union {u32 u;f32 f;} x;begin(0x150ADA68,0);effect(0);x.u=current->random;return x.f;}
u8 func_151D8E20(void){begin(0x151D8E20,0);effect(1);return (u8)current->selector;}
void func_151DBCBC(u8 selected,f32 scale,s16 alpha,s32 zero,void *point,u8 priority,s32 owner){u32 i;begin(0x151DBCBC,7);mix(selected);mix(*(u32 *)&scale);mix((u32)(s32)alpha);mix((u32)zero);mix(0xEEEEEEEE);mix(priority);mix((u32)owner);for(i=0;i<3;i++)mix(((u32 *)point)[i]);effect(2);}
static u32 identity(u8 *ptr){u32 n=(u32)ptr;
 if(n>=(u32)a&&n<(u32)a+sizeof(a))return 0x30000u+n-(u32)a;
 if(n>=(u32)v&&n<(u32)v+sizeof(v))return 0x50000u-2700+n-(u32)v;
 if(n>=(u32)p&&n<(u32)p+sizeof(p))return 0x60000u+n-(u32)p;
 if(n>=(u32)q&&n<(u32)q+sizeof(q))return 0x61000u+n-(u32)q;
 return 0xBADBAD;
}
static u32 public_hash(void){u32 h=2166136261u,i,j,addr;u8 *areas[6]={(u8 *)a,(u8 *)v,(u8 *)p,(u8 *)q,(u8 *)&D_800A73A8,(u8 *)&D_800A73B0};u32 sizes[6]={512,5500,256,256,8,4};
 for(j=0;j<6;j++)for(i=0;i<sizes[j];i++){
  if(j==0&&i>=0x94&&i<0x9C){addr=identity(*(u8 **)(actor+(i<0x98?0x94:0x98)));h=(h^((addr>>((i&3)*8))&255))*16777619u;}
  else h=(h^areas[j][i])*16777619u;
 }return h;
}
static void initialize(const Case *c){s32 i;u32 j;u8 *areas[4]={(u8 *)a,(u8 *)v,(u8 *)p,(u8 *)q};u32 sizes[4]={512,5500,256,256};union{f32 f;u32 u;} x;
 for(j=0;j<4;j++)for(i=0;i<(s32)sizes[j];i++)areas[j][i]=(u8)(i*29+90);
 for(i=-128;i<128;i++){x.f=i+3.25f;store(positions+i*20,x.u);store(positions+i*20+4,c->y);x.f=-i-4.5f;store(positions+i*20+8,x.u);}
 saved=c->alias==2?positions+c->index*20-0x48:c->alias==3?actor:(u8 *)p;
 store(saved,0x40200000u);store(saved+0x48,c->height);saved[0x1B]=0xDA;saved[0x20]=0;
 actor[0x2D]=(u8)c->index;actor[0xC]=0x83;actor[1]=0xC1;*(u8 **)(actor+0x94)=positions;*(u8 **)(actor+0x98)=saved;
 *(u64 *)&D_800A73A8=c->threshold;*(u32 *)&D_800A73B0=0xC61C4000;traceHash=2166136261u;
}
static int run(void){u32 i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;initialize(current);if(func_15189EBC(actor)!=1)return 10;if(traceHash!=current->traceHash)return 11;if(public_hash()!=current->publicHash)return 12;}return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
