"""SDK native32 with live escaped cursor, typed services and finite output cases."""
from functools import lru_cache
from tools.experiments import game_record_vertex_callback_1513e83c_candidates as c
from tools.tests import game_record_vertex_callback_1513e83c_oracle as g

FIELDS=('view','width','height','fresh','success','pattern','scale','mutation','redirect','page','seed')
REGIONS=((g.ACTOR,512),(g.BUFFER,320),(g.ALT,320),(g.PAGE,1))
def digest(data):
    h=2166136261
    for b in data:h=((h^b)*16777619)&0xFFFFFFFF
    return h
def trace(calls):
    values=[];i=0
    for t,a in calls:
        if t==g.BACKEND:a=(*a[:3],0x200,0x201)
        elif t==g.ORIENT:a=(0x100,*a[1:])
        elif t==g.MATRIX:a=(0x100,*a[1:4],0x300+i*12,0x304+i*12,0x308+i*12);i+=1
        values.extend((t,len(a),*a))
    return b''.join(g.u32(v).to_bytes(4,'little')for v in values)
@lru_cache(None)
def rows():
    result=[]
    for case in g.native_cases():
        e=g.reference(g.fixture(case,'little'),case,'little');h=digest(b''.join(g.ram.data(e['memory'],p,n)for p,n in REGIONS));th=digest(trace(e['calls']))
        values=[g.u32(getattr(case,k))for k in FIELDS]+[h,th,e['value']];result.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(result)

def harness(body=None):
    matrices=','.join('{'+','.join('0x%Xu'%g.bits(v)for v in g.matrix_values(i))+'}'for i in range(3))
    return '#include <ultra64.h>\n#include <string.h>\n#include "functions.h"\n#include "variables.h"\nvoid func_151D5D60(void *,s16,s32,Vtx **,u8 *);\nvoid func_150A7960(f32 *,f32,f32,f32,f32 *,f32 *,f32 *);\n'+(c.SELECTED if body is None else body)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef struct{u32 view,width,height,fresh,success,pattern,scale,mutation,redirect,page,seed,hash,trace,value;}Case;
static const Case cases[]={'''+rows()+r'''};
static const u32 matrices[3][16]={'''+matrices+r'''};
static u8 actor[512] __attribute__((section(".actor"),used,aligned(8)));
static u8 buffer[320] __attribute__((section(".buffer"),used,aligned(8)));
static u8 alternate[320] __attribute__((section(".alternate"),used,aligned(8)));
static u8 page __attribute__((section(".page"),used));
static const Case *current;static Vtx **cursorSlot;static u32 traceHash,copies,transforms,bad;
static void wr(u8 *p,u32 v,u32 n){u32 i;for(i=0;i<n;i++){p[i]=(u8)v;v>>=8;}}
static f32 real(u32 word){union{u32 u;f32 f;}v;v.u=word;return v.f;}
static u32 word(f32 number){union{u32 u;f32 f;}v;v.f=number;return v.u;}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
void func_151D5D60(void *p,s16 view,s32 bytes,Vtx **out,u8 *fresh){
    mix(0x151D5D60);mix(5);mix((u32)p);mix((u32)(s32)view);mix((u32)bytes);mix(0x200);mix(0x201);
    if((u32)p!=(u32)actor+0x100||bytes!=64||(u32)out-(u32)fresh!=0x35)bad=1;
    cursorSlot=out;*out=current->success?(Vtx *)(buffer+(page?0:64)):0;*fresh=(u8)current->fresh;
}
void *memcpy(void *dest,const void *src,size_t n){u32 i;u8 *d=dest;const u8 *s=src;
    mix(0x10022EC0);mix(3);mix((u32)d);mix((u32)s);mix((u32)n);if(n!=64||s!=actor+0xC0)bad=1;
    for(i=0;i<n;i++)d[i]=s[i];copies++;
    if(current->mutation&&copies==1){wr(actor+0x100+(s32)(s16)current->view*4,(u32)alternate,4);wr(actor+0x2C,word(-4.75f),4);}
    return dest;
}
void func_150A8050(f32 matrix[4][4],f32 x,f32 y,f32 z){u32 i;
    mix(0x150A8050);mix(4);mix(0x100);mix(word(x));mix(word(y));mix(word(z));
    if((u32)matrix!=(u32)cursorSlot+8)bad=1;
    for(i=0;i<16;i++)((f32 *)matrix)[i]=real(matrices[current->pattern][i]);
    if(current->mutation){wr(actor+0x34,word(-7.5f),4);wr(actor+0x50,word(-2.0f),4);wr(actor+0x2C,word(19.0f),4);}
}
void func_150A7960(f32 *matrix,f32 x,f32 y,f32 z,f32 *ox,f32 *oy,f32 *oz){f32 r[3];u32 i;
    mix(0x150A7960);mix(7);mix(0x100);mix(word(x));mix(word(y));mix(word(z));mix(0x300+transforms*12);mix(0x304+transforms*12);mix(0x308+transforms*12);
    if((u32)matrix!=(u32)cursorSlot+8||(u32)ox!=(u32)cursorSlot-0x34+transforms*12||oy!=ox+1||oz!=ox+2)bad=1;
    for(i=0;i<3;i++)r[i]=(matrix[i]*x+matrix[i+4]*y)+(matrix[i+8]*z+matrix[i+12]);
    *ox=r[0];*oy=r[1];*oz=r[2];
    if(current->redirect)*cursorSlot=(Vtx *)(alternate+transforms*16);transforms++;
}
static int run(void){u8 *p[4]={actor,buffer,alternate,&page};u32 n[4]={512,320,320,1};u32 i,j,k,h,mxcsr;Vtx *answer;
    __asm__ volatile("stmxcsr %0":"=m"(mxcsr));if(mxcsr&0xE040u)return 2;
    if((u32)actor!=0x30000||(u32)buffer!=0x60000||(u32)alternate!=0x70000||(u32)&page!=0x800BE9C0)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];for(k=0;k<4;k++)for(j=0;j<n[k];j++)p[k][j]=(u8)(j*29+current->seed*11+90);
        wr(actor+0x2C,current->width,4);wr(actor+0x30,current->height,4);
        wr(actor+0x34,word(10.5f),4);wr(actor+0x38,word(-12.25f),4);wr(actor+0x3C,word(3.75f),4);
        wr(actor+0x40,word(.25f),4);wr(actor+0x44,word(-.5f),4);wr(actor+0x48,word(1.0f),4);
        for(k=0;k<3;k++){const f32 scales[3][3]={{1,1,1},{-.5f,2,1.5f},{0,-1,3}};wr(actor+0x4C+k*4,word(scales[current->scale][k]),4);}
        wr(actor+0x100+(s32)(s16)current->view*4,(u32)buffer,4);page=(u8)current->page;traceHash=2166136261u;copies=transforms=bad=0;
        answer=func_1513E83C(actor,(s16)current->view);h=2166136261u;
        for(k=0;k<4;k++)for(j=0;j<n[k];j++)h=(h^p[k][j])*16777619u;
        if(bad||h!=current->hash||traceHash!=current->trace||(u32)answer!=current->value)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.actor=0x30000,--section-start=.buffer=0x60000,--section-start=.alternate=0x70000,--section-start=.page=0x800BE9C0']
