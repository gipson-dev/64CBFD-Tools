"""Execute original allocator and 64-bit RNG with contracted lifecycle services."""
from pathlib import Path
from unittest.mock import patch
import itertools,json,struct,sys
from tools.experiments import game_paired_actor_initializer_151951e0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_paired_actor_initializer_151951e0_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
POOL=0x800CC2D0;SEED=0x800885B0;FREE=0x15060F28;INIT=0x1505F188
class Connected(g.Oracle):
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;inside=g.RNG<=self.current_pc<g.RNG+72
  if op in(55,63):
   prior=self.own_instruction;self.own_instruction=True
   try:
    a=(self.r[rs]+((w&65535)^32768)-32768)&0xFFFFFFFF;assert a%8==0
    if op==55:self.r[rt]=self.get(a,8)
    else:self.put(a,self.r[rt],8)
   finally:self.own_instruction=prior
  elif op==0 and fn in(56,58,60,62,63):
   v=self.r[rt]&((1<<64)-1)
   if fn in(56,60):v<<=sh+(32 if fn==60 else 0)
   elif fn in(58,62):v>>=sh+(32 if fn==62 else 0)
   else:v=(v if v<1<<63 else v-(1<<64))>>(sh+32)
   self.r[rd]=v&((1<<64)-1)
  elif op==0 and fn in(37,38)and inside:self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
  elif op==0 and fn==27:
   left,right=self.r[rs]&0xFFFFFFFF,self.r[rt]&0xFFFFFFFF;assert right;self.lo,self.hi=left//right,left%right
  else:
   before=self.r[:];super().execute(w)
   if inside:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,v in enumerate(before):
     if i!=dest and v>0xFFFFFFFF:self.r[i]=v
  self.r[0]=0
 def record_call(self,t):
  if t not in(FREE,INIT):return super().record_call(t)
  args=tuple(map(g.u32,self.arguments(2 if t==FREE else 1)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append(g.actors(self.memory,self.c))
 def hook(self,t):
  if t==FREE:
   args=self.calls[-1][1];assert args==(g.PAIR,0);g.put(self.memory,args[0],0);g.put(self.memory,args[0]+0x1D4,0);self.clobber(0x87654321)
  elif t==INIT:
   assert self.calls[-1][1]==(g.PAIR,);g.effect(self.memory,self.c,g.ALLOC,());self.clobber(0x87654321)
  else:
   assert t not in(g.RNG,g.ALLOC);super().hook(t)
def machine(ws,c,code,selected,kind,seed,entry=g.ENTRY):
 m=Connected(ws,c,entry=entry,connected=code)
 for i in range(26):
  g.initialize(m.memory,POOL+812*i,c,0x50+i);g.put(m.memory,POOL+812*i,1);g.put(m.memory,POOL+812*i+0x1D4,1)
 g.initialize(m.memory,POOL,c,0);g.put(m.memory,POOL,0) # The target must activate it before allocation.
 p=POOL+812*selected
 if kind==0:g.put(m.memory,p,0)
 elif kind in(1,2):g.put(m.memory,p,0x27);g.put(m.memory,p+0x1D4,0 if kind==1 else 1)
 elif kind==4:g.put(m.memory,p,0)
 g.put(m.memory,SEED,seed,8);m.initial=dict(m.memory);return m
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
 for entry,offset,n in((g.RNG,0xDAED0,18),(g.ALLOC,0x8C1E4,95)):
  blob=rom[offset:offset+4*n];at=elf_slot_offset(elf,entry,4*n);assert elf[at:at+4*n]==blob
  code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,blob)))
 streams=g.programs();count=0;visits=set();allocations=set()
 patterns=[(i,k)for i in range(1,25)for k in(0,1,2)]+[(25,3),(25,4)]
 for selected,kind in patterns:
  for seed in SEEDS[:4]+SEEDS[-2:]:
   v=seed;values=[]
   for _ in range(5):v=next_seed(v);values.append(v&0xFFFFFFFF)
   c=g.Case(values=tuple(values),angle=32768,phase=(selected&1)*8);states=[]
   with patch.multiple(g,ACTOR=POOL,PAIR=POOL+812*selected):
    for ws in streams:
     m=machine(ws,c,code,selected,kind,seed);expected,calls,obs=g.reference(m.initial,c,True);g.put(expected,SEED,v,8);m.run()
     assert g.public(m.memory)==g.public(expected),(selected,kind,seed,'memory')
     filtered=[(call,snapshot)for call,snapshot in zip(m.calls,m.observations)if call[0]not in(FREE,INIT)]
     assert [call for call,_ in filtered]==calls
     assert [snapshot for _,snapshot in filtered]==[step['before']for step in obs]
     assert [a for t,a in m.calls if t==INIT]==[(g.PAIR,)]
     assert [a for t,a in m.calls if t==FREE]==([(g.PAIR,0)]if kind in(1,2,3)else[])
     states.append(g.final_state(m));visits.update(m.visits);allocations.add(g.PAIR)
    assert states[0]==states[1]==states[2];count+=1
 target_allocator_coverage=sum(g.ALLOC+4*i in visits for i in range(95))
 standalone=0
 for kind in(0,1,2):
  with patch.multiple(g,ACTOR=POOL,PAIR=POOL):
   ws=[code[g.ALLOC+4*i]for i in range(95)]
   m=machine(ws,g.Case(),code,0,kind,1,entry=g.ALLOC);m.run()
   assert m.r[2]==POOL and [a for t,a in m.calls if t==INIT]==[(POOL,)]
   assert [a for t,a in m.calls if t==FREE]==([(POOL,0)]if kind else[])
   visits.update(m.visits);standalone+=1
 covered_rng=sum(g.RNG+4*i in visits for i in range(18));covered_allocator=sum(g.ALLOC+4*i in visits for i in range(95))
 assert covered_rng==18 and covered_allocator==95
 controls=[]
 for label,at,expected,replacement in(('wrong-record-stride',g.ALLOC+13*4,0x2484032C,0x24840330),('wrong-rng-shift',g.RNG+8,0x000437FC,0x000437BC)):
  changed=dict(code);assert changed[at]==expected;changed[at]=replacement
  seed=1;v=seed;values=[]
  for _ in range(5):v=next_seed(v);values.append(v&0xFFFFFFFF)
  c=g.Case(values=tuple(values))
  with patch.multiple(g,ACTOR=POOL,PAIR=POOL+812):
   m=machine(streams[1],c,changed,1,0,seed)
   try:
    m.run();expected,_,_=g.reference(m.initial,c);g.put(expected,SEED,v,8);assert g.public(m.memory)==g.public(expected)
   except AssertionError:controls.append(label)
   else:raise AssertionError('ineffective original-helper control '+label)
 r=dict(cases_per_stream=count,streams=3,original_rng_words=18,covered_rng_words=covered_rng,original_allocator_words=95,target_connected_allocator_words=target_allocator_coverage,standalone_allocator_cases=standalone,covered_allocator_words=covered_allocator,selected_slots=len(allocations),source_slot_zero_never_selected_in_target=True,five_seed_transitions_checked=True,effective_controls=controls,lifecycle_services_still_modeled=True,source_installed=packet.installed(),matching_credit=0)
 (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
