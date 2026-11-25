"""Whole original primary-table parent execution with the checked child."""
from dataclasses import replace
import hashlib,itertools,json,struct
from tools.experiments import game_dual_actor_emitter_150b37c8_match as p
from tools.tests import game_dual_actor_emitter_150b37c8_guest as g
PARENT,GEOMETRY,TABLE,DELTA=0x15148ba4,0x15046c80,0x8008a430,0x800be9a4
def original(va,n,rom):return list(struct.unpack_from('>'+str(n)+'I',rom,va-0x15000000+0x2d4b0))
class Connected(g.Oracle):
 def __init__(self,words,c,count,selector,flags,collision,rom):
  self.parent_case=c;self.collision=collision;self.child_case=None;self.geometry_calls=[];self.parent_home=g.STACK+c.phase
  memory=g.fixture(c);memory[g.ACTOR+0x2e]=c.index&255;memory[g.ACTOR+0x25]=count;memory[g.ACTOR+0x7d]=0
  memory[g.RECORD+0x18]=flags;memory[g.RECORD+0x23]=selector;memory[g.RECORD+0x24]=0;g.put(memory,DELTA,g.bits(.5 if c.fcsr&1 else 1.))
  g.put(memory,TABLE+20,g.ENTRY)
  self.expected_previous=tuple(g.read(memory,g.POSITIONS+20*c.index+off)for off in(0,4,8))
  code=dict(zip(range(g.ENTRY,g.ENTRY+736,4),words))
  super().__init__(original(PARENT,143,rom),c,entry=PARENT,memory=memory,args=(g.ACTOR,),connected=code)
 def record_call(self,target):
  if target==GEOMETRY:
   args=tuple(map(g.u32,self.arguments(4)));assert args[1]==0 and args[3]==g.ACTOR+0x60
   index=(self.memory[g.ACTOR+0x2d]^128)-128;point=tuple(g.read(self.memory,args[0]+4*i)for i in range(3))
   assert point==(g.read(self.memory,g.POSITIONS+20*index),self.expected_previous[1],g.read(self.memory,g.POSITIONS+20*index+8))
   assert args[2]==g.read(self.memory,g.POSITIONS+20*index+4);self.geometry_calls.append((args,point));self.calls.append((target,args));self.events.append(('CALL',target,args));return
  if target==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(6)));assert args==(g.ACTOR,*self.expected_previous,self.parent_case.height,g.ACTOR+0x64)
   self.calls.append((target,args));self.events.append(('CALL',target,args));self.child_case=replace(self.parent_case,phase=self.r[29]-g.STACK,previous=args[1:4],height=args[4],context=args[5],fcsr=self.fcsr);self.c=self.child_case;self.counts={}
   self.child_initial=dict(self.memory);self.child_call_start=len(self.calls);self.child_observation_start=len(self.observations);return
  super().record_call(target)
 def hook(self,target):
  if target!=GEOMETRY:return super().hook(target)
  g.put(self.memory,g.MARK,g.read(self.memory,g.MARK)+1);g.put(self.memory,g.ACTOR+0x60,self.parent_case.height)
  for i in range(16):self.memory[g.ACTOR+0x64+i]=(i*7+0x46)&255
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=self.collision

def parent_cases(rom,before):
 words=original(PARENT,143,rom);data=struct.pack('>143I',*words);at=p.elf_slot_offset(before,PARENT,len(data));assert before[at:at+len(data)]==data
 programs=g.streams();raw=g.bound_blob(*g.payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),g.symbols());cases=children=controls=0;visits=set();control_rows=[]
 for count,last,flags,collision,selector,mode,rm,outcome in itertools.product((1,2,5),(0,1),(0,1),(0,1),(0,5),(0,15),(0,3),(0,1)):
  c=g.Case(index=count-1 if last else 0,mode=mode,fcsr=rm,outcome=outcome,phase=8*last,seed=count)
  models=[]
  for body in[*programs,raw]:
   m=Connected(body,c,count,selector,flags,collision,rom).run()
   assert m.r[2]==1 and m.r[29]==g.STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   if m.child_case:
    expected,calls,obs,fcsr=g.reference(m.child_initial,m.child_case)
    assert m.calls[m.child_call_start:]==calls and m.observations[m.child_observation_start:]==obs
    assert g.public(m.memory,m.child_case)==g.public(expected,m.child_case)and g.packet_snapshots(m.memory,m.child_case)==g.packet_snapshots(expected,m.child_case)and m.fcsr==fcsr
   models.append(m)
  target=models[0]
  signature=lambda m:(g.public(m.memory,m.c),m.calls,m.observations,m.r,m.f,m.fcsr,m.hi,m.lo)
  assert all(signature(m)==signature(target)for m in models[1:]);visits|={a for a in target.visits if PARENT<=a<PARENT+572};children+=int(target.child_case is not None);cases+=1
  if count==2 and flags==1 and collision==1 and selector==5 and mode==15 and rm==3:
   bad=list(programs[0]);pins=[i for i,v in enumerate(bad)if v==0x24020001];assert pins==[178];bad[pins[0]]=0x24020000
   model=Connected(bad,c,count,selector,flags,collision,rom).run();assert model.r[2]==0 and model.child_case is not None;controls+=1;control_rows.append(dict(last=last,outcome=outcome,effective_return_zero=True))
 assert children>0 and controls==4
 return dict(original_parent_cases=cases,connected_children_per_stream=children,original_parent_words=143,parent_words_visited=len(visits),parent_matches_frozen_ELF=True,whole_parent_program_executed_under_bounded_providers=True,primary_table_context_only=True,alternate_callback_branch_not_qualified_here=True,six_actual_callback_words_checked=True,effective_return_zero_controls=control_rows)

def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();assert struct.unpack_from('>I',rom,0x22ef04)[0]==g.ENTRY
 at=p.elf_slot_offset(before,TABLE+20,4);assert before[at:at+4]==g.ENTRY.to_bytes(4,'big')
 q=dict(parent='func_15148BA4',registry='D_8008A430',registry_index=5,registry_VA='0x8008A444',registry_ROM='0x22EF04',**parent_cases(rom,before),source_installed=p.installed(),matching_credit=0,helper_matching_credit=0)
 (p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
