"""Finite SDK native32 cases with typed leaf and both renderer callbacks."""
from functools import lru_cache
from dataclasses import replace
from tools.experiments import game_billboard_quad_1513ead8_candidates as c
from tools.tests import game_billboard_quad_1513ead8_oracle as g
from tools.tests.game_record_vertex_callback_1513e83c_native import digest,trace

FIELDS=('view','width','height','fresh','success','pattern','scale','mutation','redirect','page','seed','rotated','pivot','axis')
REGIONS=((g.ACTOR,512),(g.BUFFER,320),(g.ALT,320),(g.base.PAGE,1),(g.AXIS_Z,32))
WRAPPERS='''Vtx *func_1513EDB4(u8 *actor, s16 view) {
    return func_1513EAD8(actor, 0, view);
}
Vtx *func_1513EDE4(u8 *actor, s16 view) {
    return func_1513EAD8(actor, 1, view);
}'''

@lru_cache(None)
def rows():
    result=[]
    for case in g.native_cases():
        for mode in range(3):
            actual=case if mode==0 else replace(case,rotated=mode-1)
            e=g.reference(g.fixture(actual,'little'),actual,'little')
            h=digest(b''.join(g.base.ram.data(e['memory'],p,n)for p,n in REGIONS))
            values=[g.u32(getattr(case,k))for k in FIELDS]+[mode,h,digest(trace(e['calls'])),e['value']]
            result.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(result)

def harness(body=None,wrappers=None):
    axes=','.join('{'+','.join('0x%Xu'%g.bits(v)for v in pair)+'}'for pair in g.AXES)
    return '#include <ultra64.h>\n#include <string.h>\n#include "qualified-functions.h"\n#include "variables.h"\nvoid func_151D5D60(void *,s16,s32,Vtx **,u8 *);\n'+(c.SELECTED if body is None else body)+'\n'+(WRAPPERS if wrappers is None else wrappers)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef char Vertex16[sizeof(Vtx)==16?1:-1];
typedef struct{u32 view,width,height,fresh,success,pattern,scale,mutation,redirect,page,seed,rotated,pivot,axis,mode,hash,trace,value;}Case;
static const Case cases[]={'''+rows()+r'''};
static const u32 axes[6][2]={'''+axes+r'''};
static u8 actor[512] __attribute__((section(".actor"),used,aligned(8)));
static u8 buffer[320] __attribute__((section(".buffer"),used,aligned(8)));
static u8 alternate[320] __attribute__((section(".alternate"),used,aligned(8)));
static u8 page __attribute__((section(".page"),used));
f32 D_800DD1D8[4] __attribute__((section(".axisZ"),used,aligned(4)));
f32 D_800DD1E8[4] __attribute__((section(".axisX"),used,aligned(4)));
static Vtx *(*callbacks[39])(u8 *,s16)={[34]=func_1513EDB4,[35]=func_1513EDE4};
static const Case *current;static Vtx **cursorSlot;static u32 traceHash,copies,bad;
static void wr(u8 *p,u32 v,u32 n){u32 i;for(i=0;i<n;i++){p[i]=(u8)v;v>>=8;}}
static f32 real(u32 word){union{u32 u;f32 f;}v;v.u=word;return v.f;}
static u32 word(f32 number){union{u32 u;f32 f;}v;v.f=number;return v.u;}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
void func_151D5D60(void *p,s16 view,s32 bytes,Vtx **out,u8 *fresh){
    mix(0x151D5D60);mix(5);mix((u32)p);mix((u32)(s32)view);mix((u32)bytes);mix(0x200);mix(0x201);
    if((u32)p!=(u32)actor+0x100||bytes!=64)bad=1;
    cursorSlot=out;*out=current->success?(Vtx *)(buffer+(page?0:64)):0;*fresh=(u8)current->fresh;
}
void *memcpy(void *dest,const void *src,size_t n){u32 i;u8 *d=dest;const u8 *s=src;
    mix(0x10022EC0);mix(3);mix((u32)d);mix((u32)s);mix((u32)n);if(n!=64||s!=actor+0xC0)bad=1;
    for(i=0;i<n;i++)d[i]=s[i];copies++;
    if(copies==1){
        if(current->mutation){wr(actor+0x100+(s32)(s16)current->view*4,(u32)alternate,4);wr(actor+0x2C,word(-4.75f),4);wr(actor+0x50,word(.25f),4);}
        if(current->redirect)*cursorSlot=(Vtx *)(alternate+64);
    }return dest;
}
static int run(void){u8 *p[6]={actor,buffer,alternate,&page,(u8 *)D_800DD1D8,(u8 *)D_800DD1E8};u32 n[6]={512,320,320,1,16,16};u32 i,j,k,h,mxcsr;Vtx *answer;
    __asm__ volatile("stmxcsr %0":"=m"(mxcsr));if(mxcsr&0xE040u)return 2;
    if((u32)actor!=0x30000||(u32)buffer!=0x60000||(u32)alternate!=0x70000||(u32)&page!=0x800BE9C0||(u32)D_800DD1D8!=0x800DD1D8||(u32)D_800DD1E8!=0x800DD1E8)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];for(k=0;k<4;k++)for(j=0;j<n[k];j++)p[k][j]=(u8)(j*29+current->seed*11+90);
        wr(actor+0x2C,current->width,4);wr(actor+0x30,current->height,4);
        wr(actor+0x34,word(10.5f),4);wr(actor+0x38,word(-12.25f),4);wr(actor+0x3C,word(3.75f),4);
        wr(actor+0x40,word(.25f),4);wr(actor+0x44,word(-.5f),4);wr(actor+0x48,word(1.0f),4);
        for(k=0;k<3;k++){const f32 scales[3][3]={{1,1,1},{-.5f,2,1.5f},{0,-1,3}};wr(actor+0x4C+k*4,word(scales[current->scale][k]),4);}
        wr(actor+0x50,current->pivot,4);
        for(k=0;k<4;k++){D_800DD1D8[k]=real(axes[current->axis][0]);D_800DD1E8[k]=real(axes[current->axis][1]);}
        wr(actor+0x100+(s32)(s16)current->view*4,(u32)buffer,4);page=(u8)current->page;traceHash=2166136261u;copies=bad=0;
        if(current->mode)answer=callbacks[33+current->mode](actor,(s16)current->view);
        else answer=func_1513EAD8(actor,(u8)current->rotated,(s16)current->view);
        h=2166136261u;for(k=0;k<6;k++)for(j=0;j<n[k];j++)h=(h^p[k][j])*16777619u;
        if(bad||h!=current->hash||traceHash!=current->trace||(u32)answer!=current->value)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.actor=0x30000,--section-start=.buffer=0x60000,--section-start=.alternate=0x70000,--section-start=.page=0x800BE9C0,--section-start=.axisZ=0x800DD1D8,--section-start=.axisX=0x800DD1E8']
