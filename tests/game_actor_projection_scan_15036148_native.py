from pathlib import Path
import sys
from tools.experiments import game_actor_projection_scan_15036148_recovery as source
ROOT=source.ROOT
import json,subprocess
from tools.tests import game_actor_projection_scan_15036148_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body as c_body
OUT=source.OUT
def source_body():return c_body((OUT/'qualified-screen/selected-owner.c').read_text(),'func_15036148')
def rows():
    result=[]
    for c in g.cases():
        m,trace=g.reference(g.fixture(c),c)
        h=g.hashseq([v for target,args in trace for v in(target,*args)])
        result.append('{'+','.join('0x%Xu'%v for v in(c.seed,c.gate,c.mode,h,g.hashseq(g.public_values(m)),len(trace)))+'}')
    return ',\n'.join(result),len(result)
def harness(body):
    data,count=rows()
    text=r'''#include <ultra64.h>
#include "structs.h"
static const u32 cases[][6]={ROWS};
struct127 D_800CC2D0[26];
static struct108 views[2];
struct108 *D_800DBFF0;
static const u32 *current;
static u32 trace,ordinal,error;
static u16 *outputs[3];
static u32 hash(u32 h,u32 v){return(h^v)*16777619u;}
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static u32 word(f32 f){union{u32 b;f32 f;}v;v.f=f;return v.b;}
static void fill(s32 i,u32 seed,s32 force){struct127*a=&D_800CC2D0[i];u32 p=(seed+i)%12;
 a->interaction_state=1;a->unk5=i&1;
 a->x_position=real((seed+i)%3==0?0x80000000u:(seed+i)%3==1?0x7FC12345u:word((f32)(i-12)));
 a->y_position=40.0f;a->z_position=(f32)(i*3-19);a->unk28=6.0f;a->unk118=10.0f;a->unk180=-10.0f;
 if(!force){
  if(p==0)a->interaction_state=0;else if(p==1)a->unk5=255;else if(p==2)a->unk118=-10000.0f;
  else if(p==3)a->unk118=40.0f;else if(p==4)a->unk180=10.0f;else if(p==5)a->unk28=5.0f;
  else if(p==6)a->unk28=-1.0f;else if(p==7)a->unk118=real(0x7FC12345u);
  else if(p==8)a->y_position=real(0x7FC12345u);else if(p==9)a->unk180=real(0x7FC12345u);
  else if(p==10)a->unk28=real(0x7F800000u);
 }}
void func_1507C3E0(struct127 *a,u16 *height,u16 *base,u16 *radius){
 u32 i=(u32)(a-D_800CC2D0),j,value;u16*p[3]={height,base,radius};
 const u32 values[6]={0,19,20,0x7FFF,0x8000,0xFFFF};
 trace=hash(trace,0x1507C3E0u);trace=hash(trace,0x800CC2D0u+i*0x32C);
 for(j=0;j<3;j++){trace=hash(trace,0xF0010000u+j*2);if(outputs[j]&&outputs[j]!=p[j])error=1;outputs[j]=p[j];}
 if(height==base||height==radius||base==radius)error=1;
 ordinal++;value=values[(current[0]+i)%6];
 for(j=0;j<3;j++)*p[j]=(u16)(j==0?value:(current[0]+i*13+j*7)&65535u);
 if(current[2]==1){a->unk118=100.0f;a->unk180=-40.0f;}
 if(current[2]==2){a->unk118=(ordinal&1)?real(0x7FC12345u):30.0f;a->unk180=29.0f;}
 if(current[2]==3){if(i<24)fill(i+1,current[0],1);D_800DBFF0=&views[1];views[0].unk5F0=1;}
 if(current[2]==5){a->x_position=real(0x7FC12345u);a->z_position=real(0x80000000u);a->y_position=-999.0f;}
}
s32 func_15035808(s32 mode,s32 index,f32 x,f32 y,f32 z,f32 angle0,f32 angle1,f32 inner,f32 outer,f32 alpha){
 u32 args[10]={(u32)mode,(u32)index,word(x),word(y),word(z),word(angle0),word(angle1),word(inner),word(outer),word(alpha)},j;
 trace=hash(trace,0x15035808u);for(j=0;j<10;j++)trace=hash(trace,args[j]);ordinal++;
 if(current[2]==4){if(index<24)fill(index+1,current[0],1);for(j=0;j<3;j++)*outputs[j]=(u16)(ordinal*17+j);}
 return(s32)(0xB6000000u+ordinal);
}
BODY
static u32 checksum(void){u32 h=2166136261u,i,j,k,off,typed;u8*p;
 h=hash(h,D_800DBFF0==views?0x90000u:D_800DBFF0==&views[1]?0x98000u:0xDEAD0000u);
 h=hash(h,(u32)views[0].unk5F0);h=hash(h,(u32)views[1].unk5F0);
 for(i=0;i<26;i++){p=(u8*)&D_800CC2D0[i];for(j=0;j<0x32C;j++){
  off=j&~3u;typed=off==0||off==0x14||off==0x18||off==0x1C||off==0x28||off==0x118||off==0x180;
  h=hash(h,p[typed?(off+3-(j&3)):j]);}}
 for(i=0;i<2;i++){p=(u8*)&views[i];for(k=0;k<sizeof(views[i]);k++)if((k<0x5F0||k>=0x5F4)&&p[k]!=0xA5)error=1;}
 return h;}
static int run(void){u32 n,i,j;u8*p;
 if(sizeof(void*)!=4||sizeof(struct127)!=0x32C||__builtin_offsetof(struct127,unk5)!=5||
 __builtin_offsetof(struct127,x_position)!=0x14||__builtin_offsetof(struct127,y_position)!=0x18||
 __builtin_offsetof(struct127,z_position)!=0x1C||__builtin_offsetof(struct127,unk28)!=0x28||
 __builtin_offsetof(struct127,unk118)!=0x118||__builtin_offsetof(struct127,unk180)!=0x180||
 __builtin_offsetof(struct108,unk5F0)!=0x5F0)return 10;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=cases[n];p=(u8*)D_800CC2D0;for(i=0;i<sizeof(D_800CC2D0);i++)p[i]=0xA5;
  p=(u8*)views;for(i=0;i<sizeof(views);i++)p[i]=0xA5;
  for(j=0;j<26;j++)fill(j,current[0],0);
  D_800DBFF0=views;views[0].unk5F0=(s32)current[1];views[1].unk5F0=1;
  for(j=0;j<3;j++)outputs[j]=0;trace=2166136261u;ordinal=error=0;
  func_15036148();
  if(error||trace!=current[3]||ordinal!=current[5])return 11;
  if(checksum()!=current[4]||error)return 12;
 }return 0;}
'''
    # Linux enters _start without a C return address. Realign this freestanding
    # harness entry before GCC's SSE-aligned local stores; the target body and
    # normal helper calling convention stay unchanged.
    entry=START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
    return text.replace('ROWS',data).replace('BODY',body)+entry,count
def run():
    where=OUT/'native';where.mkdir(exist_ok=True);body=source_body();rows_cache=rows();valid=[];rejected={}
    # Reuse immutable generated rows across compiler/control runs.
    globals()['rows']=lambda:rows_cache
    def execute(name,text,opt):
        code,count=harness(text);p=where/(name+'.c');p.write_text(code);exe=p.with_suffix('')
        result=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        assert result.returncode==0,result.stdout+result.stderr
        return subprocess.run([str(exe)],capture_output=True,timeout=30).returncode,count
    for opt in('-O0','-O2','-O3'):
        code,count=execute(opt[1:],body,opt);assert code==0,(opt,code);valid.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True))
    controls={'unsigned-height':body.replace('(f32)(s16)heightExtent','(f32)heightExtent'),
        'short-loop':body.replace('index != 25','index != 24'),
        'inclusive-radius':body.replace('actor->unk28 > 5.0f','actor->unk28 >= 5.0f'),
        'wrong-alpha':body.replace('150.0f, 127.0f','150.0f, 126.0f'),
        'cached-height':body.replace('    f32 absentHeight;','    f32 absentHeight;\n    f32 cachedHeight;').replace('                func_1507C3E0(','                cachedHeight = actor->unk118;\n                func_1507C3E0(').replace('heightExtent < actor->unk118 -','heightExtent < cachedHeight -')}
    for name,text in controls.items():
        assert text!=body;code,_=execute(name,text,'-O2');assert code==11,(name,code);rejected[name]=code
    r=dict(valid=valid,rejected=rejected,complete_actor_objects=26,actor_size=812,view_padding_preserved=True,SDK32_offsets_checked=True,matching_credit=0)
    (OUT/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
