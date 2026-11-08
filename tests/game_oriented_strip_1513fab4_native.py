import math
from functools import lru_cache
from tools.tests import game_oriented_strip_1513fab4_oracle as g
from tools.experiments import game_oriented_strip_1513fab4_candidates as c
OUT=c.ROOT/c.BUILD
from tools.tests.game_record_vertex_callback_1513e83c_native import digest,trace
FIELDS=('view','vertexOrder','width','height','fresh','success','page','seed','widthFactor','heightFactor','geometry','viewerMode','mutation','redirect')
REGIONS=((g.ACTOR,512),(g.BUFFER,320),(g.ALT,320),(g.SCALE,8),(g.STATE,4),(g.PAGE,1),*[(g.viewer(i),12)for i in range(4)])
@lru_cache(None)
def cases():
    result=[]
    for c in g.cases():
        if c.private or c.alias or c.connected or c.phase or not 0<=g.half(c.view)<4:continue
        e=g.reference(g.fixture(c),c)
        if not all(math.isfinite(g.floating(v))and-2147483648<=g.floating(v)<2147483648 for v in e['casts']):continue
        result.append(c)
    return tuple(result)
@lru_cache(None)
def rows():
    result=[]
    for c in cases():
        e=g.reference(g.fixture(c,'little'),c,'little');payload=b''.join(bytes(e['memory'][p+i]for i in range(n))for p,n in REGIONS)
        words=[g.u32(getattr(c,n))for n in FIELDS]+[digest(payload),digest(trace(e['semantic_calls'])),e['value']]
        result.append('{'+','.join('0x%Xu'%v for v in words)+'}')
    return ',\n'.join(result)
def harness(body=None):
    body=c.CANDIDATE if body is None else body
    targets=','.join('{'+','.join('0x%Xu'%g.bits(v)for v in point)+'}'for point in g.TARGETS)
    return '#include <ultra64.h>\n#include <string.h>\nvoid func_151D5D60(void *,s16,s32,Vtx **,u8 *);\n'+body+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef char Vertex16[sizeof(Vtx)==16?1:-1];
typedef struct{u32 view,vertexOrder,width,height,fresh,success,page,seed,widthFactor,heightFactor,geometry,viewerMode,mutation,redirect,hash,trace,value;}Case;
static const Case cases[]={'''+rows()+r'''};
static const u32 targets[5][3]={'''+targets+r'''};
static u8 actor[512] __attribute__((section(".actor"),used,aligned(8)));
static u8 buffer[320] __attribute__((section(".buffer"),used,aligned(8)));
static u8 alternate[320] __attribute__((section(".alternate"),used,aligned(8)));
static f32 scale[2] __attribute__((section(".scale"),used,aligned(8)));
static u8 camera[4*0x9A0] __attribute__((section(".camera"),used,aligned(8)));
static u8 *cameraState __attribute__((section(".state"),used));
static u8 page __attribute__((section(".page"),used));
static Vtx *(*callback)(u8 *,u8,f32 *,s16)=func_1513FAB4;
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
    if((current->mutation&1)&&copies==1){wr(actor+0x100+(s32)(s16)current->view*4,(u32)alternate,4);wr(actor+0x2C,word(-4.75f),4);}
    return dest;
}
f32 *func_15144B34(s32 view){f32 *point=(f32 *)(cameraState+view*0x9A0+0x2F8);
    mix(0x15144B34);mix(1);mix((u32)view);
    if(current->mutation&2){wr(actor+0x2C,word(19.0f),4);wr(actor+0x30,word(6.5f),4);wr(actor+0x40,word(-2.0f),4);wr(actor+0x44,word(3.25f),4);wr(actor+0x48,word(8.5f),4);scale[0]=-.5f;scale[1]=2.0f;}
    return point;
}
void func_150AD8B0(f32 *h,f32 *e,f32 *side){f32 x,y,z;u32 i;
    mix(0x150AD8B0);mix(7);for(i=0;i<3;i++)mix(word(h[i]));for(i=0;i<3;i++)mix(word(e[i]));mix(0x202);
    x=h[1]*e[2]-h[2]*e[1];y=h[2]*e[0]-h[0]*e[2];z=h[0]*e[1]-h[1]*e[0];side[2]=z;side[0]=x;side[1]=y;
    if(current->mutation&4){wr(actor+0x34,word(-7.5f),4);wr(actor+0x38,word(2.25f),4);wr(actor+0x3C,word(-9.5f),4);wr(actor+0x2C,0,4);scale[0]=8.0f;}
    if(current->redirect)*cursorSlot=(Vtx *)(alternate+64);
}
f32 sqrtf(f32 input){f32 answer;__asm__ volatile("sqrtss %1,%0":"=x"(answer):"x"(input));return answer;}
static int run(void){u8 *p[10]={actor,buffer,alternate,(u8 *)scale,(u8 *)&cameraState,&page,camera+0x2F8,camera+0xC98,camera+0x1638,camera+0x1FD8};u32 n[10]={512,320,320,8,4,1,12,12,12,12};u32 i,j,k,h,mxcsr;Vtx *answer;
    __asm__ volatile("stmxcsr %0":"=m"(mxcsr));if(mxcsr&0xE040u)return 2;
    if((u32)actor!=0x30000||(u32)buffer!=0x60000||(u32)alternate!=0x70000||(u32)scale!=0xB0000||(u32)camera!=0xC0000||(u32)&cameraState!=0x800DBFF0||(u32)&page!=0x800BE9C0)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        const f32 centers[3]={10.5f,-12.25f,3.75f};const f32 oldScale[3]={-.5f,2.0f,1.5f};current=&cases[i];
        for(k=0;k<3;k++)for(j=0;j<n[k];j++)p[k][j]=(u8)(j*29+current->seed*11+90);
        wr(actor+0x2C,current->width,4);wr(actor+0x30,current->height,4);scale[0]=real(current->widthFactor);scale[1]=real(current->heightFactor);
        for(k=0;k<3;k++){wr(actor+0x34+k*4,word(centers[k]),4);wr(actor+0x40+k*4,targets[current->geometry][k],4);wr(actor+0x4C+k*4,word(oldScale[k]),4);}
        for(j=0;j<4;j++)for(k=0;k<3;k++){f32 point=current->viewerMode==0?(k==0?(f32)j*1.25f:k==1?(f32)j*-.5f:20.0f+(f32)j*2.0f):current->viewerMode==1?(k==0?11.0f+(f32)j:k==1?-10.0f-(f32)j*2.0f:-5.0f+(f32)j*.25f):centers[k]+((real(targets[current->geometry][k])-centers[k])*(real(current->height)*real(current->heightFactor)))*.5f;wr(camera+j*0x9A0+0x2F8+k*4,word(point),4);}
        cameraState=camera;page=(u8)current->page;wr(actor+0x100+(s32)(s16)current->view*4,(u32)buffer,4);traceHash=2166136261u;copies=bad=0;
        answer=callback(actor,(u8)current->vertexOrder,scale,(s16)current->view);h=2166136261u;
        for(k=0;k<10;k++)for(j=0;j<n[k];j++)h=(h^p[k][j])*16777619u;
        if(bad||h!=current->hash||traceHash!=current->trace||(u32)answer!=current->value)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
LINK_FLAGS=['-Wl,--section-start=.actor=0x30000,--section-start=.buffer=0x60000,--section-start=.alternate=0x70000,--section-start=.scale=0xB0000,--section-start=.camera=0xC0000,--section-start=.state=0x800DBFF0,--section-start=.page=0x800BE9C0']
