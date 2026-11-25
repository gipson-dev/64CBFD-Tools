"""The sole original call window, shared cleanup and its actual epilogue path."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_owner_effect_factory_151c6ea0_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_owner_effect_factory_151c6ea0_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.patch_generated_slice_ld import load_game_data_layout
r=target_packet.ROOT;PARENT,WINDOW,CHILD_END,COMMON,EPILOGUE0,EPILOGUE1=0x1505f298,0x15060284,0x15060294,0x150603d4,0x15060448,0x1506044c
EVENT,CLEANUP,INPUT,OTHER,COEFF=0x1505e650,0x15060a30,0x70000,0x72000,0x80099688
@lru_cache(maxsize=1)
def coefficient():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,COEFF,4);blob=elf[at:at+4];start,base,_,_=load_game_data_layout(r/'conker');assert blob==(r/'conker/conker.us.bin').read_bytes()[start+COEFF-base:start+COEFF-base+4];return blob
class TrackedWindow(WindowCode):
 def __getitem__(self,pc):
  if pc in self.ends:self.owner.boundary_pc=pc
  return super().__getitem__(pc)
def parent_effect(m,c,t,ordinal,mutate):
 g.put(m,g.MARK+4,g.read(m,g.MARK+4)+1)
 if mutate:m[c.point+0x81]=3 if ordinal&1 else 2
def post_reference(initial,c,frame,fcsr,mutate):
 m=dict(initial);calls=[];obs=[]
 def call(t,a):
  nonlocal fcsr
  calls.append((t,a));obs.append((t,a,g.data(m,c.point,512),g.data(m,g.OUTPUT-32,448),g.data(m,frame,144),fcsr));parent_effect(m,c,t,len(calls),mutate)
  for i in range(4):g.put(m,frame+4*i,0xb6000000+i)
  fcsr=c.rm|0x400*len(calls)
 timer=g.read(m,frame+0x8c)
 if timer:
  for at in (16,20,24):g.put(m,frame+at,0)
  call(EVENT,(c.point,timer&65535,g.read(m,frame+0x84),g.read(m,frame+0x7c),0,0,0))
 other=g.read(m,frame+0x88)
 if other:call(CLEANUP,(other,c.point))
 value=m[c.point+0x81]
 if value&7==2 and not g.read(m,INPUT,2)&0x8000:
  m[c.point+0x81]=(value-1)&255;g.put(m,c.point+0x24,g.read(m,COEFF))
 return m,calls,obs,fcsr,value
class Connected(g.Machine):
 def __init__(self,leaf,c,parent,timer,other,status,buttons,mutate,change=None,poison=None):
  memory=g.fixture(c);memory.update({c.point+i:(i*29+c.seed+90)&255 for i in range(512)});memory[c.point+59]=c.identity;memory[c.point+0x81]=status
  memory.update({INPUT+i:0x5a for i in range(16)});memory.update({OTHER+i:0x5a for i in range(16)});g.put(memory,INPUT,buttons,2);g.put(memory,g.MARK+4,0)
  # Pin the actual cleanup coefficient before using it in the bounded fixture.
  blob=coefficient()
  for i,v in enumerate(blob):memory[COEFF+i]=v
  super().__init__(leaf,c,memory=memory,args=(c.point,INPUT));self.outer=c;self.frame=g.home(c)-144;self.mutate=mutate;self.poison=poison;self.child_args=[];self.post_calls=[];self.post_obs=[];self.parent_visits=set()
  self.code.update(parent)
  if change:
   for at,w in change.items():self.code[at]=w
  self.code=TrackedWindow(self.code,self);self.entry=PARENT;self.code.ends=(PARENT+24,)
  try:self.run();raise AssertionError('Missing prologue boundary')
  except WindowBoundary:pass
  assert self.r[29]==self.frame
  for at,v in ((0x7c,0x3f800000),(0x84,0x3f800000),(0x88,OTHER if other else 0),(0x8c,timer)):g.put(self.memory,self.frame+at,v)
  self.entry=WINDOW;self.code.ends=(CHILD_END,)
 def record_call(self,t):
  if t==g.ENTRY:
   a=tuple(self.arguments(3));self.child_args.append(a);self.c=replace(self.outer,phase=self.outer.phase-144,point=a[0],slot=a[1],context=a[2]);self.child_expected=g.reference(self.memory,self.c,self.r[31]);return
  if t in(EVENT,CLEANUP):
   a=tuple(self.arguments(7 if t==EVENT else 2));self.post_calls.append((t,a));self.post_obs.append((t,a,g.data(self.memory,self.outer.point,512),g.data(self.memory,g.OUTPUT-32,448),g.data(self.memory,self.frame,144),self.fcsr));return
  super().record_call(t)
 def hook(self,t):
  if t not in(EVENT,CLEANUP):return super().hook(t)
  parent_effect(self.memory,self.outer,t,len(self.post_calls),self.mutate)
  for i in range(4):self.put(self.r[29]+4*i,0xb6000000+i,4)
  for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa6000000+i
  self.f[:20]=[0xa6000000+i for i in range(20)];self.r[2]=0xdeadbeef;self.fcsr=self.outer.rm|0x400*len(self.post_calls)
 def finish(self):
  try:self.run();raise AssertionError('Missing child return boundary')
  except WindowBoundary:pass
  wanted,calls,obs,fcsr,v0=self.child_expected;assert(self.memory,self.calls,self.observations,self.fcsr,self.r[2])==(wanted,calls,obs,fcsr,v0)
  self.expected=post_reference(wanted,self.outer,self.frame,fcsr,self.mutate);self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
  self.entry=CHILD_END;self.code.ends=(EPILOGUE0,EPILOGUE1)
  try:self.run();raise AssertionError('Missing original epilogue boundary')
  except WindowBoundary:pass
  self.actual_epilogue=self.boundary_pc;self.cleanup_memory=dict(self.memory);self.cleanup_v0=self.r[2];self.cleanup_fcsr=self.fcsr;self.entry=self.actual_epilogue;self.code.ends=();self.run();return self
 def verify(self):
  wanted,calls,obs,fcsr,v0=self.expected
  assert self.child_args==[(self.outer.point,255,1)],'original fixed call arguments'
  assert self.memory==wanted and self.post_calls==calls and self.post_obs==obs and self.cleanup_fcsr==fcsr and self.cleanup_v0==v0,dict(reason='original cleanup and overwritten V0',memory_equal=self.memory==wanted,calls_equal=self.post_calls==calls,observations_equal=self.post_obs==obs,actual_fcsr=self.cleanup_fcsr,expected_fcsr=fcsr,actual_v0=self.cleanup_v0,expected_v0=v0,first_differences=[hex(a)for a in self.memory if self.memory[a]!=wanted.get(a)][:12])
  assert all(self.r[i]==self.before[i]for i in (*range(16,24),28,29,30,31));return self
def main():
 full=(o/'original-parent.s').read_text();rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',full);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(rows)==1137 and blob==(r/'conker/conker.us.bin').read_bytes()[0x8c748:0x8d90c];parent={int(va,16):int(w,16)for _,va,w in rows}
 programs=[g.bound_blob(*g.payload(o/f,'func_151C6EA0'),g.symbols())for f in ('original-target.o','selected-owner.o')];cases=[]
 for outcome,mutation,timer,other,status,buttons,mutate,phase in itertools.product((0,1),(0,7),(0,0x12340001),(0,1),(1,2,255),(0,0x8000),(0,1),(0,8)):
  cases.append((g.Case(outcome=outcome,mutation=mutation,phase=phase,identity=(status*17+mutation)&255,rm=phase//8),timer,other,status,buttons,mutate))
 epilogues=set();poison_checks=0
 for c,*args in cases:
  models=[Connected(ws,c,parent,*args).finish().verify()for ws in programs];a,z=models;assert g.state(a)==g.state(z)and a.post_calls==z.post_calls and a.post_obs==z.post_obs;epilogues.add(a.actual_epilogue)
  if c.mutation==0 and not args[0]and not args[1]:
   for poison in (0x80000000,0xdead1234):Connected(programs[0],c,parent,*args,poison=poison).finish().verify();poison_checks+=1
 controls=[]
 for name,change in [('slot',{0x15060288:0x240500fe}),('context',{0x15060290:0x24060002}),('missing-V0-overwrite',{0x15060400:0,0x1506040c:0})]:
  m=Connected(programs[0],g.Case(),parent,0,0,2,0,0,change=change).finish()
  try:m.verify()
  except AssertionError:controls.append(dict(name=name,complete_bounded_execution=True,rejected=True))
  else:raise AssertionError('Ineffective caller control')
 q=dict(parent_words_pinned=1137,parent_frame=144,cases_per_stream=len(cases),streams=2,actual_prologue_words=6,call_window='15060284..150602A4',common_cleanup='150603D4..15060448',actual_separate_epilogue_entries=[hex(v)for v in sorted(epilogues)],actual_epilogue_words=[5,4],all_fixed_three_arguments_and_child_frame_and_full_parent_cleanup_memory_equal=True,child_incidental_V0_poison_checks=poison_checks,child_return_ignored=True,optional_post_helpers_contracted=True,parent_dispatch_and_preceding_sound_call_are_preconditions=True,complete_parent_runtime_not_qualified=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
