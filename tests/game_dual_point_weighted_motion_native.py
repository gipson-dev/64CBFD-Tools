"""SDK native32 flat-float storage, real timestep aliases and independent rows."""
from dataclasses import replace
from tools.experiments import game_dual_point_weighted_motion_candidates as c
from tools.tests import game_dual_point_weighted_motion_oracle as g
from tools.tests.test_game_row_destination_fill import START
def program(controls):
    cases=list(g.cases());layouts=(-1,*g.INPUTS);rows=[]
    for i in range(2048):
        case=replace(cases[i*97%len(cases)],layout=layouts[i%len(layouts)]);initial=g.fixture(case);expected=g.reference(initial,case);actor=g.owner(case)
        rows.append('{%d,0x%08Xu,{%s},{%s}}'%(case.layout,case.step,','.join('0x%08Xu'%g.read(initial,actor+n)for n in g.INPUTS),','.join('0x%08Xu'%g.read(expected,actor+n)for n in g.WRITTEN)))
    text='#include <ultra64.h>\nstatic f32 *timestep;\n#define D_800BE9A4 (*timestep)\n'
    for name,body in dict(selected=c.SELECTED,**controls).items():text+=body.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef char float_width[sizeof(f32)==4?1:-1];
typedef char word_width[sizeof(u32)==4?1:-1];
typedef struct {s32 layout;u32 step,input[12],output[9];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
typedef union {u32 u;f32 f;} Float;
static f32 real(u32 u){Float x;x.u=u;return x.f;}
static u32 word(f32 f){Float x;x.f=f;return x.u;}
static int nanword(u32 x){return (x&0x7f800000u)==0x7f800000u&&(x&0x7fffffu)!=0;}
static struct {u32 left[4];f32 fields[0x144/4];u32 right[4];} actual,wanted;
static f32 externalStep;
typedef s32(*Update)(u8*);
__attribute__((noinline,noclone))static s32 invoke(Update fn,u8*p){return fn(p);}
static int variant(Update fn,u32 wrapped){
 const u32 inputs[12]={0x34,0x38,0x3c,0x40,0x44,0x48,0x130,0x134,0x138,0x13c,0x140,0x54};
 const u32 outputs[9]={0x34,0x38,0x3c,0x40,0x44,0x48,0x130,0x134,0x138};
 u32 i,j,a,b;u8*p=(u8*)&actual,*q=(u8*)&wanted;
 for(i=0;i<2048;i++){
  for(j=0;j<sizeof(actual);j++)p[j]=(u8)(j*13+89);
  for(j=0;j<12;j++)actual.fields[inputs[j]/4]=real(rows[i].input[j]);
  externalStep=real(rows[i].step);timestep=rows[i].layout<0?&externalStep:actual.fields+(u32)rows[i].layout/4;
  for(j=0;j<sizeof(actual);j++)q[j]=p[j];
  for(j=0;j<9;j++)wanted.fields[outputs[j]/4]=real(rows[i].output[j]);
  if((wrapped?invoke(fn,(u8*)actual.fields):fn((u8*)actual.fields))!=1)return 1;
  for(j=0;j<9;j++){
   a=word(actual.fields[outputs[j]/4]);b=word(wanted.fields[outputs[j]/4]);
   if(nanword(a)&&nanword(b))actual.fields[outputs[j]/4]=wanted.fields[outputs[j]/4];
  }
  for(j=0;j<sizeof(actual);j++)if(p[j]!=q[j])return 1;
  if(rows[i].layout<0&&word(externalStep)!=rows[i].step)return 1;
 }return 0;
}
static int run(void){if(sizeof(void*)!=4)return 99;
 if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,n in enumerate(controls):text+=' if(variant(%s,0)!=1)return %d;\n'%(n,i+2)
    return text+'return 0;}\n'+START
