"""Native32 complete body, typed caller and separately compiled matrix adapter."""
from tools.experiments import game_overlay_projection as source
from tools.tests import game_overlay_projection_oracle as model
from tools.tests import game_view_point_projection_native as matrix

HEADER='''#include <ultra64.h>
typedef struct {
 u8 padding00[12];f32 extentX,extentY;u8 padding14[16];
 f32 top,bottom,left,right;u8 padding34[332];
} OverlayViewport1AC2F0;
typedef union {u32 words[768];f32 floats[768];OverlayViewport1AC2F0 views[8];} ViewBank;
extern ViewBank bank;extern f32 matrices[8][4][4];extern u32 output[16];
extern u8 *viewBase;extern f32 (*outputBase)[2];extern u32 calls;
#define D_800BE628 viewBase
#define OVERLAY_VIEWS_1AC2F0 ((OverlayViewport1AC2F0 *)D_800BE628)
#define D_800D9D10 (&matrices[2])
#define D_800DDDE8 outputBase
void func_150A7A00(f32 matrix[4][4],f32 x,f32 y,f32 z,f32*,f32*,f32*,f32*);
void func_1517F814(s32,f32,f32,f32,s32);
void invoke(s32,f32,f32,f32,s32);
'''
HELPER=matrix.HELPER.replace('void func_150A7A00','extern u32 calls;\nvoid func_150A7A00').replace(
 ' f32 result[4];int i;',' f32 result[4];int i;calls++;')
CALLER=HEADER+'void invoke(s32 mode,f32 x,f32 y,f32 z,s32 view){func_1517F814(mode,x,y,z,view);}\n'


def cases():
    for memory,args in model.corpus():
        view=model.signed(args[4])
        if view not in (0,1,3) or model.read(memory,model.LIMITS)!=model.bits(10000.):continue
        expected,_,_=model.reference(memory,args)
        row=(model.read(memory,model.BASE)+args[4]*384)&model.MASK
        out=(model.OUTPUT+args[4]*8)&model.MASK;index=(2+view)*96
        target=index+(out-row)//4 if row<=out<row+384 else 768+4+view*2
        fields=[model.read(memory,(row+p)&model.MASK) for p in (12,16,36,44)]
        address=(model.MATRICES+args[4]*64)&model.MASK
        values=[model.read(memory,(address+i*4)&model.MASK) for i in range(16)]
        yield (*args,target,*fields,*values,model.read(expected,out),model.read(expected,(out+4)&model.MASK))


def program():
    rows=['{'+','.join('0x%Xu'%v for v in row)+'}' for row in cases()]
    return HEADER+'''
static const u32 cases[][28]={'''+',\n'.join(rows)+'''};
ViewBank bank;f32 matrices[8][4][4];u32 output[16],calls;u8 *viewBase;f32 (*outputBase)[2];
static u32 initial[784];
static void die(u32 n){__asm__ volatile("int $0x80"::"a"(1),"b"(n):"memory");__builtin_unreachable();}
static f32 scalar(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static int nanword(u32 v){return (v&0x7F800000u)==0x7F800000u&&(v&0x7FFFFFu);}
static u32 word(u32 i){return i<768?bank.words[i]:output[i-768];}
static f32 *pointer(u32 i){return i<768?&bank.floats[i]:(f32*)&output[i-768];}
static void run(void){u32 n,i,j,row,target,wanted,actual;const u32*c;
 if(sizeof(void*)!=4||sizeof(OverlayViewport1AC2F0)!=384||
  __builtin_offsetof(OverlayViewport1AC2F0,extentX)!=12||__builtin_offsetof(OverlayViewport1AC2F0,extentY)!=16||
  __builtin_offsetof(OverlayViewport1AC2F0,top)!=36||__builtin_offsetof(OverlayViewport1AC2F0,left)!=44)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=cases[n];row=2+c[4];target=c[5];
  for(i=0;i<768;i++)bank.words[i]=0xA5A5A5A5u;
  for(i=0;i<16;i++)output[i]=0xA5A5A5A5u;
  for(i=0;i<128;i++)((u32*)matrices)[i]=0xA5A5A5A5u;
  for(i=0;i<16;i++)((u32*)matrices[row])[i]=c[10+i];
  bank.words[row*96+3]=c[6];bank.words[row*96+4]=c[7];
  bank.words[row*96+9]=c[8];bank.words[row*96+11]=c[9];
  viewBase=(u8*)&bank.views[2];
  outputBase=(f32(*)[2])(pointer(target)-c[4]*2);
  for(i=0;i<784;i++)initial[i]=word(i);
  calls=0;invoke((s32)c[0],scalar(c[1]),scalar(c[2]),scalar(c[3]),(s32)c[4]);
  if(calls!=(c[0]==0)||viewBase!=(u8*)&bank.views[2]||outputBase!=(f32(*)[2])(pointer(target)-c[4]*2))die(22);
  for(i=0;i<784;i++){wanted=initial[i];
   for(j=0;j<2;j++)if(i==target+j)wanted=c[26+j];
   actual=word(i);if(actual!=wanted&&!(i>=target&&i<target+2&&nanword(actual)&&nanword(wanted)))die(22);
  }
  for(i=0;i<128;i++){wanted=0xA5A5A5A5u;if(i>=row*16&&i<row*16+16)wanted=c[10+i-row*16];
   if(((u32*)matrices)[i]!=wanted)die(22);}
 }}
void _start(void){run();die(0);}
'''


def controls(body):
    return dict(inverted_mode=body.replace('screenSpace == 0','screenSpace != 0'),
        wrong_matrix=body.replace('(u32)view * 64U','(u32)view * 16U'),
        missing_zero_fallback=body.replace('divisor = 1.0f','divisor = 2.0f'),
        missing_division=body.replace('/ divisor','* divisor'),
        wrong_y_sign=body.replace('record->extentY - projectedY','record->extentY + projectedY'),
        wrong_upper=body.replace('10000.0f','1000.0f'),
        unordered_nan=body.replace('10000.0f < projectedX','!(projectedX <= 10000.0f)'),
        swapped_outputs=body.replace('&projectedX, &projectedY, &projectedZ, &divisor','&projectedY, &projectedX, &projectedZ, &divisor'))
