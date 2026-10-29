"""Private actor-state model: ordered float effects, helper mutations and dispatch."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-actor-state-completion-match';F='func_150BE210';ENTRY=0x150BE210;ACTOR=0x30000
SYMS=dict(func_1511650C=0x1511650C,func_100111C8=0x100111C8)
@dataclass(frozen=True)
class Case:
 state:int=0
 flag:int=4
 angle:int=0x43B40000
 speed:int=0x3F800000
 handle:int=0x8001
 mutation:int=0
 phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(256)})
 m[ACTOR+0x73]=c.state;m[ACTOR+0x4F]=c.flag;put(m,ACTOR+0x84,c.angle);put(m,ACTOR+0x64,c.speed);put(m,ACTOR+0x74,c.handle,2);return m
def effect(m,c,stop=False):
 if not stop:
  if c.mutation==1:m[ACTOR+0x4F]^=4;put(m,ACTOR+0x74,0xFFFF,2)
  elif c.mutation==2:m[ACTOR+0x4F]=4;put(m,ACTOR+0x84,bits(360.0));put(m,ACTOR+0x64,bits(1.0));put(m,ACTOR+0x74,0x8001,2)
  elif c.mutation==3:m[ACTOR+0x73]=0x83;m[ACTOR+0x4F]=4;put(m,ACTOR+0x84,bits(400.0));put(m,ACTOR+0x64,0)
  elif c.mutation==4:m[ACTOR+0x4F]=4;put(m,ACTOR+0x84,bits(500.0));put(m,ACTOR+0x64,0)
 elif c.mutation==4:
  put(m,ACTOR+0x74,0xFFFF,2);put(m,ACTOR+0x64,bits(-12.5));m[ACTOR+0x73]=0xA2
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[]
 if m[ACTOR+0x73]&3==3:return m,calls,observations
 calls.append((s['func_1511650C'],(ACTOR,1,0x62C,0x43FA0000)));effect(m,c)
 if m[ACTOR+0x4F]&4:put(m,ACTOR+0x84,bits(floating(read(m,ACTOR+0x84))+floating(read(m,ACTOR+0x64))))
 elif floating(read(m,ACTOR+0x84))>270.0:put(m,ACTOR+0x84,bits(270.0))
 if floating(read(m,ACTOR+0x84))>360.0:
  m[ACTOR+0x73]&=0xFC;m[ACTOR+0x73]|=3;put(m,ACTOR+0x64,0);handle=read(m,ACTOR+0x74,2)
  observations.append((m[ACTOR+0x73],read(m,ACTOR+0x64),handle));calls.append((s['func_100111C8'],(handle,)));effect(m,c,True);put(m,ACTOR+0x74,0,2)
 return m,calls,observations
public=lambda m:{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.stop_observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,))
 def record_call(self,t):
  assert t in(self.syms['func_1511650C'],self.syms['func_100111C8'],ENTRY),hex(t);n=4 if t==self.syms['func_1511650C']else 1;args=tuple(self.arguments(n));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.syms['func_100111C8']:self.stop_observations.append((self.memory[ACTOR+0x73],read(self.memory,ACTOR+0x64),read(self.memory,ACTOR+0x74,2)))
 def hook(self,t):
  stop=t==self.syms['func_100111C8'];assert stop or t==self.syms['func_1511650C'];assert self.r[29]==STACK+self.case.phase-32
  assert read(self.memory,self.r[29]+24)==self.before[16];assert read(self.memory,self.r[29]+28)==getattr(self,'expected_target_ra',self.before[31]);effect(self.memory,self.case,stop)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEAD0000+int(stop)
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
ANGLES=(0x80000000,0,bits(-1.0),bits(269.99997),bits(270.0),bits(270.00003),bits(359.99997),bits(360.0),bits(360.00003),0x7F7FFFFF,0x7FC12345,0xFF800000)
SPEEDS=(0,0x80000000,bits(1.0),bits(-1.0),0x7F800000,0x7FC54321)
def cases():
 for state,phase in itertools.product((3,0x83,0xFF),(0,8)):yield Case(state=state,phase=phase)
 for args in itertools.product((0,1,2,0xFE),(0,4,255),ANGLES,SPEEDS,(0,0x8001),range(5),(0,8)):yield Case(*args)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def reachable_offsets(words):
 todo=[0];seen=set();processed=set();size=len(words)*4
 while todo:
  at=todo.pop()
  if at in processed:continue
  assert 0<=at<size and at%4==0,hex(at);processed.add(at);seen.add(at);w=words[at//4];op=w>>26;rs=w>>21&31;rt=w>>16&31;fn=w&63
  if op==0 and fn==8:
   assert rs==31;seen.add(at+4);continue
  if op==3:seen.add(at+4);todo.append(at+8);continue
  branch=op in(4,5,6,7,20,21,22,23)or(op==17 and rs==8)
  if branch:
   seen.add(at+4);imm=((w&65535)^32768)-32768;target=at+4+imm*4
   if op==4 and rs==rt:todo.append(target)
   elif op==5 and rs==rt:todo.append(at+8)
   else:todo.extend((target,at+8))
  else:todo.append(at+4)
 return seen

def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);want,calls_expected,observations=reference(initial,c);machines=[]
  for i,words in enumerate(programs):
   m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls,m.stop_observations)==(public(want),calls_expected,observations),(c,i);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]),c;visited.update(machines[0].visits);count+=1
 reachable=reachable_offsets(programs[0]);assert reachable==set(range(0,216,4))-{0x60} and programs[0][0x60//4]==0x44811000;assert visited=={ENTRY+i for i in reachable},(len(visited),sorted(visited));print(dict(guest_cases=count,covered_reachable_words=len(visited),unreachable_offsets=['0x60']),flush=True)
 prefixes=0
 for c in(Case(state=3),Case(angle=bits(400.0),speed=0),Case(flag=0,angle=bits(300.0)),Case(mutation=4,phase=8),Case(angle=0x7FC12345),Case(mutation=3)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missed access boundary',c,cut))
    pair.append(m)
   assert state(pair[0])==state(pair[1])==state(pair[2]);prefixes+=1
 c=Case(state=0xFF);m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};m[ACTOR+0x73]=c.state
 for words in programs:machine=Oracle(words,m,c).run();assert public(machine.memory)==public(m)and machine.calls==[]
 rebased=0
 for k,(entry,helper,stop)in enumerate(((0x15001000,0x10007FF0,0x10008000),(0x1F008000,0x1F108000,0x1000FFF0),(0x1000FFF0,0x10008000,0x10007FF0))):
  s=dict(func_1511650C=helper,func_100111C8=stop);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]
  for args in itertools.product((0,3,0xFE),(0,4),(bits(270),bits(360),bits(400),0x7FC12345),(0,3,4),(0,8)):
   c=Case(state=args[0],flag=args[1],angle=args[2],mutation=args[3],phase=args[4]);initial=fixture(c);want,calls_expected,observations=reference(initial,c,s)
   for words in ps:machine=Oracle(words,initial,c,s,entry).run();assert(public(machine.memory),machine.calls,machine.stop_observations)==(public(want),calls_expected,observations)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>3I',rom,0x22D9A8)==(ENTRY,0,0);assert (0x80088EE8-0x80088C90)//12==50;window=list(struct.unpack_from('>5I',rom,0x141390));caller_count=0
 for c in(Case(state=s,flag=f,angle=a,mutation=mu,phase=ph)for s,f,a,mu,ph in itertools.product((0,3,0xFE),(0,4),(bits(270),bits(360),bits(400)),(0,3,4),(0,8))):
  initial=fixture(c);put(initial,ACTOR+0x38,ENTRY);want,calls_expected,observations=reference(initial,c)
  for words in programs:
   connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));connected[0x15113EF4]=0;m=Oracle(window,initial,c,entry=0x15113EE0,connected=connected);m.r[16]=ACTOR;m.r[30]=7;m.before=m.r[:];m.expected_target_ra=0x15113EF0;m.code=WindowCode(m.code,m);m.code.ends=(0x15113EF4,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing original dispatch boundary')
   assert(public(m.memory),m.calls,m.stop_observations,m.r[30])==(public(want),[(ENTRY,(ACTOR,))]+calls_expected,observations,8)
  caller_count+=1
 q=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,retail_words=54,covered_reachable_words=53,unreachable_offsets=['0x60'],static_CFG_certified=True,raw_C_byte_exact=True,frame=32,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,quiet_NaN_and_float_boundaries=True,helper_field_mutations=True,stop_boundary_observations=True,access_prefix_pairs=prefixes,sparse_completed_state=True,rebase_layouts=3,rebase_cases=rebased,registration_table='D_80088C90',registration_index=50,registration_stride=12,registration_ROM='0x22D9A8',caller_window_entry='0x15113EE0',caller_window_words=5,caller_window_cases=caller_count,result_register_ignored=True,providers_bounded=True,hardware_FCSR_or_complete_parent_claimed=False)
 return q


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_150BE210';body=selected[selected.index('/* Advance'):]
 mutants=dict(whole_byte_gate=body.replace('(actor[0x73] & 3) != 3','actor[0x73] != 3'),inclusive_finish=body.replace('> 360.0f','>= 360.0f'),wrong_clamp=body.replace('270.0f','360.0f'),cached_phase=body.replace('        func_1511650C(actor, 1, 0x62C, 500.0f);','        f32 saved = *(f32 *)(actor + 0x84);\n        func_1511650C(actor, 1, 0x62C, 500.0f);\n        *(f32 *)(actor + 0x84) = saved;'),late_speed_clear=body.replace('            *(f32 *)(actor + 0x64) = 0.0f;\n            func_100111C8(*(u16 *)(actor + 0x74));','            func_100111C8(*(u16 *)(actor + 0x74));\n            *(f32 *)(actor + 0x64) = 0.0f;'),omit_stop=body.replace('            func_100111C8(*(u16 *)(actor + 0x74));','            (void)0;'),recheck_state=body.replace('        func_1511650C(actor, 1, 0x62C, 500.0f);','        func_1511650C(actor, 1, 0x62C, 500.0f);\n        if ((actor[0x73] & 3) == 3) return;'));assert all(v!=body for v in mutants.values())
 text=r'''#include <ultra64.h>
 typedef struct {u32 state,flag,angle,speed,handle,mutation,outState,outFlag,outAngle,outSpeed,outHandle,calls,stopState,stopSpeed,stopHandle;} Fixture;
 static u8 actorData[256] __attribute__((aligned(8)));static const Fixture*current;static s32 firstCalls,stopCalls,badArgs;static u32 observedState,observedSpeed,observedHandle;
 static f32 asFloat(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
 static u32 asBits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
 static s32 nanBits(u32 u){return (u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu)!=0;}
 void func_1511650C(u8*a,s32 b,s32 c,f32 d){firstCalls++;if(a!=actorData||b!=1||c!=0x62C||asBits(d)!=0x43FA0000u)badArgs=1;
  if(current->mutation==1){actorData[0x4F]^=4;*(u16*)(actorData+0x74)=0xFFFF;}
  else if(current->mutation==2){actorData[0x4F]=4;*(f32*)(actorData+0x84)=360.0f;*(f32*)(actorData+0x64)=1.0f;*(u16*)(actorData+0x74)=0x8001;}
  else if(current->mutation==3){actorData[0x73]=0x83;actorData[0x4F]=4;*(f32*)(actorData+0x84)=400.0f;*(f32*)(actorData+0x64)=0.0f;}
  else if(current->mutation==4){actorData[0x4F]=4;*(f32*)(actorData+0x84)=500.0f;*(f32*)(actorData+0x64)=0.0f;}}
 void func_100111C8(u16 handle){stopCalls++;observedState=actorData[0x73];observedSpeed=asBits(*(f32*)(actorData+0x64));observedHandle=handle;
  if(current->mutation==4){*(u16*)(actorData+0x74)=0xFFFF;*(f32*)(actorData+0x64)=-12.5f;actorData[0x73]=0xA2;}}
 '''
 text+='\n'.join(b.replace(F,'test_'+name)for name,b in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0];rows=[]
 for c in cases:
  initial=q.fixture(c);want,calls,observations=q.reference(initial,c);obs=observations[0]if observations else(0,0,0);rows.append((c.state,c.flag,c.angle,c.speed,c.handle,c.mutation,want[q.ACTOR+0x73],want[q.ACTOR+0x4F],q.read(want,q.ACTOR+0x84),q.read(want,q.ACTOR+0x64),q.read(want,q.ACTOR+0x74,2),len(calls),*obs))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef void(*Fn)(u8*);
 static s32 field(s32 i){return i==0x4F||(i>=0x64&&i<0x68)||i==0x73||i==0x74||i==0x75||(i>=0x84&&i<0x88);}
 static s32 check(Fn fn){s32 n,i;u32 angle;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;current=c;for(i=0;i<256;i++)actorData[i]=(u8)(i*29+0x59);actorData[0x73]=(u8)c->state;actorData[0x4F]=(u8)c->flag;*(f32*)(actorData+0x84)=asFloat(c->angle);*(f32*)(actorData+0x64)=asFloat(c->speed);*(u16*)(actorData+0x74)=(u16)c->handle;firstCalls=stopCalls=badArgs=0;observedState=observedSpeed=observedHandle=0;fn(actorData);
  if(badArgs||firstCalls!=(c->calls!=0)||stopCalls!=(c->calls==2))return 1;
  if(actorData[0x73]!=c->outState||actorData[0x4F]!=c->outFlag||*(u16*)(actorData+0x74)!=c->outHandle||asBits(*(f32*)(actorData+0x64))!=c->outSpeed)return 2;
  angle=asBits(*(f32*)(actorData+0x84));if(angle!=c->outAngle&&!(nanBits(angle)&&nanBits(c->outAngle)))return 3;
  if(observedState!=c->stopState||observedSpeed!=c->stopSpeed||observedHandle!=c->stopHandle)return 4;
  for(i=0;i<256;i++)if(!field(i)&&actorData[i]!=(u8)(i*29+0x59))return 5;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
