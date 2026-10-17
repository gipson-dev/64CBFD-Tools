"""Native32 complete SDK body and separately compiled typed caller controls."""
import itertools
import math
from tools.experiments import game_clipped_rectangle as source
from tools.tests import game_clipped_rectangle_oracle as model

HEADER='''#include <ultra64.h>
typedef struct {
 u8 padding00[12];f32 extentX,extentY;u8 padding14[16];
 f32 top,bottom,left,right;u8 padding34[332];
} OverlayViewport1AC2F0;
typedef union {u32 words[768];f32 floats[768];OverlayViewport1AC2F0 views[8];Gfx commands[384];} ViewBank;
extern ViewBank bank;extern Gfx output[8];extern u8 *viewBase;
#define OVERLAY_VIEWS_1AC2F0 ((OverlayViewport1AC2F0 *)viewBase)
Gfx *func_1517F9F4(Gfx *,s32,s32,s32,s32,s32);
Gfx *invoke(Gfx *,s32,s32,s32,s32,s32);
'''
CALLER=HEADER+'''Gfx *invoke(Gfx *p,s32 x0,s32 y0,s32 x1,s32 y1,s32 view){
 return func_1517F9F4(p,x0,y0,x1,y1,view);
}
'''


def cases():
    for view,endpoint,bound,alias in itertools.product((0,1,3),range(len(model.ENDPOINTS)),range(len(model.BOUNDS)),(0,1)):
        if not all(math.isfinite(v) and -2147483648.<=v<2147483648. for v in model.BOUNDS[bound]):continue
        memory,args=model.fixture(view,endpoint,bound)
        row=model.VIEWS+view*384;target=768+4
        if alias:
            args=(row+40,*args[1:]);target=(2+view)*96+10
        expected,_,emitted=model.reference(memory,args)
        coords=[model.read(memory,row+at) for at in (36,40,44,48)]
        yield (*args[1:],target,*coords,model.read(expected,args[0]),model.read(expected,args[0]+4),int(emitted))


def program():
    rows=['{'+','.join('0x%Xu'%v for v in row)+'}' for row in cases()]
    return HEADER+'''
static const u32 cases[][13]={'''+',\n'.join(rows)+'''};
ViewBank bank;Gfx output[8];u8 *viewBase;static u32 initial[784];
static void die(u32 n){__asm__ volatile("int $0x80"::"a"(1),"b"(n):"memory");__builtin_unreachable();}
static u32 word(u32 i){return i<768?bank.words[i]:((u32*)output)[i-768];}
static Gfx *pointer(u32 i){return i<768?&bank.commands[i/2]:&output[(i-768)/2];}
static void run(void){u32 n,i,j,row,target,wanted;const u32*c;Gfx*result;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(OverlayViewport1AC2F0)!=384||
  __builtin_offsetof(OverlayViewport1AC2F0,top)!=36||__builtin_offsetof(OverlayViewport1AC2F0,left)!=44)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=cases[n];row=2+c[4];target=c[5];
  for(i=0;i<768;i++)bank.words[i]=0xA5A5A5A5u;
  for(i=0;i<16;i++)((u32*)output)[i]=0xA5A5A5A5u;
  for(j=0;j<4;j++)bank.words[row*96+9+j]=c[6+j];
  for(i=0;i<784;i++)initial[i]=word(i);
  viewBase=(u8*)&bank.views[2];
  result=invoke(pointer(target),(s32)c[0],(s32)c[1],(s32)c[2],(s32)c[3],(s32)c[4]);
  if(result!=pointer(target)+c[12]||viewBase!=(u8*)&bank.views[2])die(22);
  for(i=0;i<784;i++){wanted=initial[i];
   if(c[12])for(j=0;j<2;j++)if(i==target+j)wanted=c[10+j];
   if(word(i)!=wanted)die(22);
  }
 }}
void _start(void){run();die(0);}
'''


def controls(body):
    return dict(no_x_sort=body.replace('if (right < left)','if (0)'),
        no_y_sort=body.replace('if (bottom < top)','if (0)'),
        inclusive_edges=body.replace('>=','>'),
        baked_view=body.replace('OVERLAY_VIEWS_1AC2F0[view]','OVERLAY_VIEWS_1AC2F0[0]'),
        wrong_low_x=body.replace('left < scratch ? scratch','left < scratch ? clipRight'),
        missing_y_clip=body.replace('top < clipTop ? clipTop : clipBottom < top ? clipBottom : top','top'),
        swapped_x=body.replace('commands++, left, top, right, bottom','commands++, right, top, left, bottom'),
        changed_edge=body.replace('commands++, left, top, right, bottom','commands++, left, top, right ^ 1, bottom'))
