"""SDK native32 backing with actual float aliases and byte flags in struct171."""
from dataclasses import replace
from tools.experiments import game_dual_extent_approach_candidates as c
from tools.tests import game_dual_extent_approach_oracle as g
from tools.tests.test_game_row_destination_fill import START

def program():
    corpus=list(g.cases()); rows=[]; layouts=(-1,0x2C,0x30,0x118,0x128)
    for i in range(2048):
        case=corpus[(i*97)%len(corpus)]
        initial=g.fixture(case); layout=layouts[i%5]
        if layout>=0:
            # One constant aliases real float storage; other constants stay
            # external. Keep the independent reference's live reloads.
            constants=g.CONSTANT
            value=g.FACTORS[(i//5)%4]; index=(i//5)%4
            g.put(initial,case.at+layout,value)
            # Model the same single alias by relocating its reads/stores.
            addresses=[constants+4*j for j in range(4)]; addresses[index]=case.at+layout
        else:index=0;addresses=[g.CONSTANT+4*j for j in range(4)]
        expected,calls=reference_addresses(initial,case,addresses)
        fields=','.join('0x%08Xu'%g.read(initial,case.at+n) for n in g.FIELDS)
        output=','.join('0x%08Xu'%g.read(expected,case.at+n) for n in g.FIELDS)
        rows.append('{%d,%d,%d,{%s},{%s},%d,%d,%d,%d}'%(
            case.flags,layout,index,fields,output,expected[case.at+0x74],expected[case.at+0x71],len(calls),case.phase))
    text='''#include <ultra64.h>
#include "structs.h"
static f32 *constants[4];
#define D_800A57A0 (*constants[0])
#define D_800A57A4 (*constants[1])
#define D_800A57A8 (*constants[2])
#define D_800A57AC (*constants[3])
static u32 calls, bad;
void func_1513F680(struct171 *p,u8 a,u8 b,u8 d,u8 e){
 if(a!=0x80||b!=4||d!=0xFE||e!=0xFF)bad=1;
 calls++;p->unk70=a;p->unk71=b;p->unk72=d;p->unk73=e;
}
typedef struct {struct171 prefix;u8 gap[0x98];f32 targetX;u8 gap2[12];f32 targetY;} Owner;
typedef char prefix_size[sizeof(struct171)==0x80?1:-1];
typedef char owner_size[sizeof(Owner)==0x12C?1:-1];
typedef char target_x[__builtin_offsetof(Owner,targetX)==0x118?1:-1];
typedef char target_y[__builtin_offsetof(Owner,targetY)==0x128?1:-1];
typedef char flags_byte[__builtin_offsetof(struct171,unk74)==0x74?1:-1];
'''
    for name,body in dict(selected=c.SELECTED,**g.controls()).items():text+=body.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef struct {s32 flags,layout,index;u32 input[4],output[4];u32 flag,slot,calls,phase;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
static struct {u32 left[4];Owner owner;u32 right[4];} actual,wanted;
static f32 external[4];
typedef union {u32 u;f32 f;} Float;
static f32 real(u32 u){Float v;v.u=u;return v.f;}
static u32 word(f32 f){Float v;v.f=f;return v.u;}
static int nanword(u32 u){return(u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu);}
typedef s32(*Update)(u8*);
__attribute__((noinline,noclone))static s32 invoke(Update fn,u8*p){return fn(p);}
static int variant(Update fn,u32 wrapped){
 u32 i,j;u8*a=(u8*)&actual,*b=(u8*)&wanted;
 f32 *fields[4]={&actual.owner.prefix.unk2C,&actual.owner.prefix.unk30,&actual.owner.targetX,&actual.owner.targetY};
 f32 *wantedFields[4]={&wanted.owner.prefix.unk2C,&wanted.owner.prefix.unk30,&wanted.owner.targetX,&wanted.owner.targetY};
 for(i=0;i<2048;i++){
  for(j=0;j<sizeof(actual);j++)a[j]=(u8)(j*13+89);
  for(j=0;j<4;j++){*fields[j]=real(rows[i].input[j]);external[j]=real((j&1)?0x3F733333u:0x3F333333u);constants[j]=&external[j];}
  if(rows[i].layout>=0){
   for(j=0;j<4;j++)if((u8*)fields[j]-(u8*)&actual.owner==rows[i].layout)constants[rows[i].index]=fields[j];
  }
  ((u8*)&actual.owner)[0x70]=0x80;((u8*)&actual.owner)[0x71]=5;
  ((u8*)&actual.owner)[0x72]=0xFE;((u8*)&actual.owner)[0x73]=0xFF;
  ((u8*)&actual.owner)[0x74]=(u8)rows[i].flags;
  for(j=0;j<sizeof(actual);j++)b[j]=a[j];
  for(j=0;j<4;j++)*wantedFields[j]=real(rows[i].output[j]);
  ((u8*)&wanted.owner)[0x74]=(u8)rows[i].flag;((u8*)&wanted.owner)[0x71]=(u8)rows[i].slot;
  calls=bad=0;
  if((wrapped?invoke(fn,(u8*)&actual.owner):fn((u8*)&actual.owner))!=1||calls!=rows[i].calls||bad)return 1;
  for(j=0;j<4;j++)if(nanword(word(*fields[j]))&&nanword(rows[i].output[j]))*fields[j]=real(rows[i].output[j]);
  for(j=0;j<sizeof(actual);j++)if(a[j]!=b[j])return 1;
  for(j=0;j<4;j++)if(constants[j]==&external[j]&&word(external[j])!=((j&1)?0x3F733333u:0x3F333333u))return 1;
 }return 0;
}
static int run(void){if(sizeof(void*)!=4)return 99;
 if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,name in enumerate(g.controls()):text+=' if(variant(%s,0)!=1)return %d;\n'%(name,i+2)
    return text+'return 0;}\n'+START

def reference_addresses(initial,c,addresses):
    # Deliberately independent scalar implementation for native storage, with
    # each constant address chosen separately rather than assuming adjacency.
    m=dict(initial);complete=True
    for off,target,mask,k in ((0x2C,0x118,2,0),(0x30,0x128,8,2)):
        if m[c.at+0x74]&mask:continue
        old=g.floating(g.read(m,c.at+off));end=g.floating(g.read(m,c.at+target))
        delta=g.floating(g.bits(end-old));factor=g.floating(g.read(m,addresses[k]))
        result=g.bits(old+g.floating(g.bits(delta*factor)));g.put(m,c.at+off,result)
        boundary=g.bits(g.floating(g.read(m,c.at+target))*g.floating(g.read(m,addresses[k+1])))
        if g.floating(boundary)<g.floating(g.read(m,c.at+off)):m[c.at+0x74]|=mask
        else:complete=False
    if complete:m[c.at+0x71]=4
    return m,[1]if complete else[]
