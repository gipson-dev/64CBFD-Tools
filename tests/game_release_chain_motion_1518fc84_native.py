import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_release_chain_motion_1518fc84_match as p
out=p.out;root=p.root
from tools.tests import game_release_chain_motion_1518fc84_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_1518FC84')
 controls={
  'release_arg':('func_1516972C((struct102 *)child)','func_1516972C((struct102 *)owner)'),
  'delta':('target->unk0 - owner->origin.unk0','owner->origin.unk0 - target->unk0'),
  'velocity_scale':('* parameters->velocityScale','* -parameters->velocityScale'),
  'random_range':('randomScale * parameters->randomRange','randomScale * parameters->fixedValue'),
  'fixed_value':('child->fixedValue = parameters->fixedValue','child->fixedValue = parameters->randomBase'),
  'low':('child->low = parameters->low','child->low = parameters->high'),
  'high':('child->high = parameters->high','child->high = parameters->low'),
  'timer_base':('+ parameters->timerBase','- parameters->timerBase'),
  'timer_range':('parameters->timerRange + 1','parameters->timerRange + 2'),
  'callback':('? 0x21 : 0x20','? 0x20 : 0x20'),
  'event':('child->event = 0x24','child->event = 0x25'),
  'flags':('child->flags |= 0x08000001','child->flags |= 0x08000000'),
 }
 code=r'''#include <ultra64.h>
 #include "structs.h"
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct ReleaseChainNode ReleaseChainNode;
 typedef struct {u8 reserved00[0x60];f32 velocityScale,randomBase,randomRange,fixedValue;s16 low,high,timerBase,timerRange;u8 reserved78[4];u8 flags;} ReleaseMotionParameters1518FC84;
 typedef struct {u8 reserved00[0x1C];s16 timer;u8 reserved1E[0x3A];u32 flags;u8 reserved5C[0x10];s16 low,high;u8 callback,event;u8 reserved72[0xD6];f32 velocity[3],randomValue,fixedValue;} ReleaseMotionChild1518FC84;
 typedef struct {u8 reserved00[0x2C];ReleaseMotionChild1518FC84 *child;ReleaseMotionParameters1518FC84 *parameters;struct17 origin;} ReleaseMotionOwner1518FC84;
 _Static_assert(__builtin_offsetof(ReleaseMotionOwner1518FC84,child)==0x2c && __builtin_offsetof(ReleaseMotionOwner1518FC84,origin)==0x34 && __builtin_offsetof(ReleaseMotionChild1518FC84,velocity)==0x148 && __builtin_offsetof(ReleaseMotionParameters1518FC84,flags)==0x7c,"layout");
 struct Case {s32 present,alias,mutate,flag,span;u32 rng,scale;s32 null_target;u32 velocity[3],random_value,fixed_value;s32 low,high,timer,callback,event;u32 child_flags;s32 released,ncalls,calls[2];};
 static const struct Case cases[]={
 '''
 kinds={g.RELEASE:1,g.RANDOM_FLOAT:2,g.RANDOM_INT:3}
 for c in g.cases():
  m,calls=g.reference(c);vals=[c.present,c.alias,c.mutate,c.flag,c.span,c.rng,g.bits(c.scale),c.null_target];velocity=[g.read(m,g.CHILD+0x148+4*i)for i in range(3)];floats=[g.read(m,g.CHILD+0x154),g.read(m,g.CHILD+0x158)];shorts=[g.signed16(g.read(m,g.CHILD+off,2))for off in (0x6c,0x6e,0x1c)];rest=[*shorts,m[g.CHILD+0x70],m[g.CHILD+0x71],g.read(m,g.CHILD+0x58),int(g.read(m,g.MARK)==0x13579bdf),len(calls)];cv=[kinds[t] for t,_ in calls]+[0]*(2-len(calls))
  code+='{'+','.join('0x%Xu'%v if i in(5,6)else str(v)for i,v in enumerate(vals))+',{'+','.join('0x%Xu'%v for v in velocity)+'},'+','.join('0x%Xu'%v for v in floats)+','+','.join('0x%Xu'%v if i==5 else str(v)for i,v in enumerate(rest))+',{'+','.join(map(str,cv))+'}},\n'
 initial=g.fixture(g.cases()[0]);initvel=[g.read(initial,g.CHILD+0x148+4*i)for i in range(3)];initfloat=[g.read(initial,g.CHILD+0x154),g.read(initial,g.CHILD+0x158)];initshort=[g.signed16(g.read(initial,g.CHILD+off,2))for off in (0x6c,0x6e,0x1c)];initbyte=[initial[g.CHILD+0x70],initial[g.CHILD+0x71]]
 code+='};\nstatic const u32 initial_velocity[3]={'+','.join('0x%Xu'%v for v in initvel)+'};\nstatic const u32 initial_float[2]={'+','.join('0x%Xu'%v for v in initfloat)+'};\nstatic const s32 initial_short[3]={'+','.join(map(str,initshort))+'};\nstatic const u8 initial_byte[2]={'+','.join(map(str,initbyte))+'};\n'
 code+=r'''
 static ReleaseMotionChild1518FC84 *current_child;static ReleaseMotionParameters1518FC84 *current_parameters;static const struct Case *current_case;static int calls,observed[2],released,bad;
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(const f32*src){u32 x=0,i;u8*d=(u8*)&x;const u8*s=(const u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 static s32 signed_word(u32 x){s32 y;u8*d=(u8*)&y,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];return y;}
 static void event(int kind){if(calls>=2){bad=1;return;}observed[calls++]=kind;}
 void func_1516972C(struct102 *p){event(1);if((void*)p!=(void*)current_child)bad=1;released=1;}
 f32 func_150ADA68(void){event(2);if(current_case->mutate){current_parameters->randomBase=10.f;current_parameters->randomRange=-2.f;current_parameters->fixedValue=17.f;current_parameters->low=-7;current_parameters->high=12;}return .5f;}
 s32 func_150ADA20(void){event(3);if(current_case->mutate){current_parameters->timerBase=13;current_parameters->timerRange=3;current_parameters->flags^=1;}return signed_word(current_case->rng);}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_1518FC84','test_'+key,1)+'\n'
 code+=r'''
 typedef void(*T)(ReleaseChainNode*,void*);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];ReleaseMotionOwner1518FC84 owner;ReleaseMotionChild1518FC84 child;ReleaseMotionParameters1518FC84 parameters;struct17 separate,*target;u8 before[sizeof child],owner_before[sizeof owner];u8*p=(u8*)&child,*o=(u8*)&owner;
  for(i=0;i<sizeof child;i++)p[i]=(i*13+11)&255;for(i=0;i<sizeof owner;i++)o[i]=(i*13+11)&255;owner.child=&child;owner.parameters=c->present?&parameters:NULL;owner.origin.unk0=1.f;owner.origin.unk4=-2.f;owner.origin.unk8=3.f;separate.unk0=4.f;separate.unk4=1.f;separate.unk8=-1.f;target=c->null_target?NULL:c->alias?&owner.origin:&separate;
  put_bits(&parameters.velocityScale,c->scale);parameters.randomBase=2.f;parameters.randomRange=-.5f;parameters.fixedValue=5.f;parameters.low=-11;parameters.high=22;parameters.timerBase=-100;parameters.timerRange=c->span;parameters.flags=c->flag;
  put_bits(&child.velocity[0],initial_velocity[0]);put_bits(&child.velocity[1],initial_velocity[1]);put_bits(&child.velocity[2],initial_velocity[2]);put_bits(&child.randomValue,initial_float[0]);put_bits(&child.fixedValue,initial_float[1]);child.low=initial_short[0];child.high=initial_short[1];child.timer=initial_short[2];child.callback=initial_byte[0];child.event=initial_byte[1];child.flags=0x01020304;
  for(i=0;i<sizeof child;i++)before[i]=p[i];for(i=0;i<sizeof owner;i++)owner_before[i]=o[i];current_child=&child;current_parameters=&parameters;current_case=c;calls=released=bad=0;test((ReleaseChainNode*)&owner,target);
  if(bad||calls!=c->ncalls||released!=c->released)return 1;for(i=0;i<(u32)calls;i++)if(observed[i]!=c->calls[i])return 2;
  if(get_bits(&child.velocity[0])!=c->velocity[0]||get_bits(&child.velocity[1])!=c->velocity[1]||get_bits(&child.velocity[2])!=c->velocity[2]||get_bits(&child.randomValue)!=c->random_value||get_bits(&child.fixedValue)!=c->fixed_value||child.low!=c->low||child.high!=c->high||child.timer!=c->timer||child.callback!=c->callback||child.event!=c->event||child.flags!=c->child_flags)return 3;
  for(i=0;i<sizeof child;i++)if((!c->present||((i<0x1c||i>=0x1e)&&(i<0x58||i>=0x5c)&&(i<0x6c||i>=0x72)&&(i<0x148||i>=0x15c)))&&p[i]!=before[i])return 4;
  for(i=0;i<sizeof owner;i++)if(o[i]!=owner_before[i])return 5;
  if(c->present&&c->mutate&&(parameters.randomBase!=10.f||parameters.randomRange!=-2.f||parameters.fixedValue!=17.f||parameters.low!=-7||parameters.high!=12||parameters.timerBase!=13||parameters.timerRange!=3||parameters.flags!=(c->flag^1)))return 6;
  }return 0;}
 static int run(void){int selected_result=check(test_selected);if(selected_result)return selected_result;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_1518FC84_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_1518FC84_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers='modeled',valid_finite_inputs_and_owner_target_alias=True,zero_divisor_excluded=True,source_installed=False);(out/'native_1518FC84_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
