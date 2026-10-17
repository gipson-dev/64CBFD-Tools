"""Native32 full SDK candidate, typed caller and effective semantic controls."""
import itertools
from tools.experiments import game_mirrored_texture_rectangles as source
from tools.tests import game_mirrored_texture_oracle as model

HEADER='''#include <ultra64.h>
typedef struct {u8 pad0[12];f32 extentX,extentY;u8 pad14[364];} OverlayViewport1AC2F0;
typedef union {u32 words[768];OverlayViewport1AC2F0 views[8];Gfx commands[384];} ViewBank;
typedef union {u32 words[32];f32 points[16][2];Gfx commands[16];} PointBank;
extern ViewBank bank;extern PointBank pointBank;extern Gfx output[16];
extern u8 *viewBase;extern f32 (*pointBase)[2];
#define OVERLAY_VIEWS_1AC2F0 ((OverlayViewport1AC2F0 *)viewBase)
#define D_800DDDE8 pointBase
Gfx *func_1517FB9C(Gfx *,s32,s32,f32,f32,s32);
Gfx *invoke(Gfx *,s32,s32,f32,f32,s32);
'''
CALLER=HEADER+'''Gfx *invoke(Gfx*p,s32 size,s32 texture,f32 x,f32 y,s32 view){
 return func_1517FB9C(p,size,texture,x,y,view);
}
'''


def fixtures():
    for view,size,texture,center,offset in itertools.product((0,1,3),(1,3,32),
            (0,32,65535,0x200000,0x3FFFFF),range(5),range(4)):
        yield model.fixture(view,size,texture,center,offset)
    for view,size,center,alias in itertools.product((0,1,3),(1,32),(0,2,3,4),(2,3)):
        yield model.fixture(view,size,64,center,1,alias)


def cases():
    for memory,args in fixtures():
        cursor,size,texture,x,y,view=args;row=model.VIEWS+view*384;point=model.PROJECTED+view*8
        target=(2+view)*96 if cursor==row else 768+(2+view)*2-2 if cursor==point-8 else 768+32+4
        _,_,words,_=model.reference(memory,args)
        yield (size,texture,x,y,view,target,model.read(memory,row+12),model.read(memory,row+16),
            model.read(memory,point),model.read(memory,point+4),*words)


def program():
    rows=['{'+','.join('0x%Xu'%v for v in row)+'}' for row in cases()]
    return HEADER+'''
static const u32 cases[][34]={'''+',\n'.join(rows)+'''};
ViewBank bank;PointBank pointBank;Gfx output[16];u8 *viewBase;f32 (*pointBase)[2];static u32 initial[832];
static void die(u32 n){__asm__ volatile("int $0x80"::"a"(1),"b"(n):"memory");__builtin_unreachable();}
static f32 scalar(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(u32 i){return i<768?bank.words[i]:i<800?pointBank.words[i-768]:((u32*)output)[i-800];}
static Gfx *pointer(u32 i){return i<768?&bank.commands[i/2]:i<800?&pointBank.commands[(i-768)/2]:&output[(i-800)/2];}
static void run(void){u32 n,i,j,row,target,wanted;const u32*c;Gfx*result;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(OverlayViewport1AC2F0)!=384||
  __builtin_offsetof(OverlayViewport1AC2F0,extentX)!=12||__builtin_offsetof(OverlayViewport1AC2F0,extentY)!=16)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=cases[n];row=2+c[4];target=c[5];
  for(i=0;i<768;i++)bank.words[i]=0xA5A5A5A5u;
  for(i=0;i<32;i++)pointBank.words[i]=((u32*)output)[i]=0xA5A5A5A5u;
  bank.words[row*96+3]=c[6];bank.words[row*96+4]=c[7];
  pointBank.words[row*2]=c[8];pointBank.words[row*2+1]=c[9];
  viewBase=(u8*)&bank.views[2];pointBase=&pointBank.points[2];
  for(i=0;i<832;i++)initial[i]=word(i);
  result=invoke(pointer(target),(s32)c[0],(s32)c[1],scalar(c[2]),scalar(c[3]),(s32)c[4]);
  if(result!=pointer(target)+12||viewBase!=(u8*)&bank.views[2]||pointBase!=&pointBank.points[2])die(22);
  for(i=0;i<832;i++){wanted=initial[i];for(j=0;j<24;j++)if(i==target+j)wanted=c[10+j];if(word(i)!=wanted)die(22);}
 }}
void _start(void){run();die(0);}
'''


def controls(body):
    return dict(baked_view=body.replace('OVERLAY_VIEWS_1AC2F0[view]','OVERLAY_VIEWS_1AC2F0[0]'),
        omitted_projection=body.replace('D_800DDDE8[view][0]','0.0f').replace('D_800DDDE8[view][1]','0.0f'),
        wrong_ratio=body.replace('1024.0f','512.0f'),
        wrong_x_direction=body.replace('-step,','step,'),
        wrong_y_direction=body.replace(', -step);',', step);'),
        wrong_phase=body.replace('31 -','32 -'),
        wrong_quarter_units=body.replace('* 4','* 2'))
