"""Typed native32 state, field timestep aliases and independently generated rows."""
from dataclasses import replace
from tools.experiments import game_dual_damped_motion_candidates as c
from tools.tests import game_dual_damped_motion_oracle as g
from tools.tests.test_game_row_destination_fill import START
def source(controls):
    cases=list(g.corpus());rows=[];layouts=(-1,*g.INPUTS)
    for i in range(2048):
        case=replace(cases[i*97%len(cases)],layout=layouts[i%16]);initial=g.fixture(case);expected=g.reference(initial,case);actor=g.owner(case)
        inputs=[g.read(initial,actor+at)for at in g.INPUTS];outputs=[g.read(expected,actor+at)for at in g.WRITTEN]
        rows.append('{%d,0x%08Xu,{%s},{%s}}'%(i%16-1,case.step,','.join('0x%08Xu'%v for v in inputs),','.join('0x%08Xu'%v for v in outputs)))
    text='typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;\n'
    text+=c.DECLARATIONS.replace('extern f32 D_800BE9A4;','')
    text+='static f32 *timestep;\n#define D_800BE9A4 (*timestep)\n'
    for name,body in dict(selected=c.SELECTED,**controls).items():text+=body.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef char size_check[sizeof(DualDampedMotion15197AB4)==0x164?1:-1];
typedef char position_check[__builtin_offsetof(DualDampedMotion15197AB4,position)==0x34?1:-1];
typedef char velocity_check[__builtin_offsetof(DualDampedMotion15197AB4,velocity)==0x140?1:-1];
typedef char end_velocity_check[__builtin_offsetof(DualDampedMotion15197AB4,endVelocity)==0x14C?1:-1];
typedef char acceleration_check[__builtin_offsetof(DualDampedMotion15197AB4,verticalAcceleration)==0x158?1:-1];
typedef char damping_check[__builtin_offsetof(DualDampedMotion15197AB4,damping)==0x15C?1:-1];
typedef char end_damping_check[__builtin_offsetof(DualDampedMotion15197AB4,endDamping)==0x160?1:-1];
typedef struct {s32 layout;u32 step,input[15],output[12];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
static struct {u8 left[16];DualDampedMotion15197AB4 m;u8 right[16];} actual,expected;
static f32 externalStep;
typedef union {u32 u;f32 f;} Float;
static f32 real(u32 v){Float x;x.u=v;return x.f;}
static u32 word(f32 v){Float x;x.f=v;return x.u;}
static f32 *field(DualDampedMotion15197AB4*p,u32 i){if(i<3)return p->position+i;if(i<6)return p->endPoint+(i-3);
 if(i<9)return p->velocity+(i-6);if(i<12)return p->endVelocity+(i-9);
 if(i==12)return &p->verticalAcceleration;if(i==13)return &p->damping;return &p->endDamping;}
static int isnanword(u32 x){return (x&0x7F800000u)==0x7F800000u&&(x&0x7FFFFFu)!=0;}
typedef s32(*Update)(DualDampedMotion15197AB4*);
__attribute__((noinline,noclone))static s32 invoke(Update fn,DualDampedMotion15197AB4*p){return fn(p);}
static int variant(Update fn,u32 typed){u32 i,j,a,b;u8*p=(u8*)&actual,*q=(u8*)&expected;
 for(i=0;i<2048;i++){
  for(j=0;j<sizeof(actual);j++)p[j]=(u8)(j*13+89);
  for(j=0;j<15;j++)*field(&actual.m,j)=real(rows[i].input[j]);
  externalStep=real(rows[i].step);timestep=rows[i].layout<0?&externalStep:field(&actual.m,(u32)rows[i].layout);
  for(j=0;j<sizeof(actual);j++)q[j]=p[j];
  for(j=0;j<12;j++)*field(&expected.m,j)=real(rows[i].output[j]);
  if((typed?invoke(fn,&actual.m):fn==selected?selected(&actual.m):fn(&actual.m))!=1)return 1;
  for(j=0;j<12;j++){a=word(*field(&actual.m,j));b=word(*field(&expected.m,j));
   if(isnanword(a)&&isnanword(b))*field(&actual.m,j)=*field(&expected.m,j);}
  for(j=0;j<sizeof(actual);j++)if(p[j]!=q[j])return 1;
  if(rows[i].layout<0&&word(externalStep)!=rows[i].step)return 1;
 }return 0;}
static int run(void){if(sizeof(void*)!=4)return 99;
 if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,name in enumerate(controls):text+=' if(variant(%s,0)!=1)return %d;\n'%(name,i+2)
    return text+'return 0;}\n'+START
