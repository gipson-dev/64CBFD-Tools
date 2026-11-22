"""Literal query,64-bit RNG and narrow sound wrapper; setup/deeper leaves contracted."""
from pathlib import Path
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_record_sound_scheduler_150d0730_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_record_sound_scheduler_150d0730_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED=0x800885B0;LIMIT=0x800D3094;MASK=0x800D2340;BITS=0x800D30F0
SHIFT=0x10026800;COLLISION=0x150A1DA0;AUDIO=0x10010E78;ACTOR=0x800CC2D0
PROVIDERS=((g.RNG,0xDAED0,18),(g.QUERY,0xCFE78,73),(g.SOUND,0x10F88,29))
@lru_cache(maxsize=1)
def inputs():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
 for entry,offset,n in PROVIDERS:
  blob=rom[offset:offset+n*4];at=elf_slot_offset(elf,entry,n*4);assert elf[at:at+n*4]==blob
  code.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,blob)))
 return code
class Connected(g.Oracle):
 def __init__(self,words,c,seed,fast,limit):
  super().__init__(words,c,connected=inputs());self.leaves=[];self.seeds=[]
  g.put(self.memory,SEED,seed,8);g.put(self.memory,LIMIT,limit);g.put(self.memory,MASK,fast,2)
  bits=sum(1<<i for i,reply in zip(g.INDICES,c.replies)if not reply);g.put(self.memory,BITS,bits,8)
  self.initial=dict(self.memory)
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  inside=g.RNG<=self.current_pc<g.RNG+72
  if op in(55,63):
   prior=self.own_instruction;self.own_instruction=True
   try:
    address=g.u32(self.r[rs]+((w&65535)^32768)-32768);assert address%8==0
    if op==55:self.r[rt]=self.get(address,8)
    else:self.put(address,self.r[rt],8)
   finally:self.own_instruction=prior
  elif op==0 and fn in(56,58,60,62,63):
   value=self.r[rt]&((1<<64)-1)
   if fn in(56,60):value<<=sh+(32 if fn==60 else 0)
   elif fn in(58,62):value>>=sh+(32 if fn==62 else 0)
   else:value=(value if value<1<<63 else value-(1<<64))>>(sh+32)
   self.r[rd]=value&((1<<64)-1)
  elif op==0 and fn in(37,38)and inside:self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
  elif op==0 and fn==27:
   left,right=self.r[rs]&0xFFFFFFFF,self.r[rt]&0xFFFFFFFF;assert right
   self.lo,self.hi=left//right,left%right
  else:
   before=self.r[:];super().execute(w)
   if inside:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,v in enumerate(before):
     if i!=dest and v>0xFFFFFFFF:self.r[i]=v
  self.r[0]=0
 def record_call(self,t):
  if t not in(SHIFT,COLLISION,AUDIO):
   super().record_call(t)
   if t==g.RNG:self.seeds.append(g.read(self.memory,SEED,8))
   return
  args=tuple(map(g.u32,self.arguments(4 if t==SHIFT else 3 if t==COLLISION else 11)));self.leaves.append((t,args))
 def hook(self,t):
  if t==g.SETUP:return super().hook(t)
  args=self.leaves[-1][1]
  if t==SHIFT:
   value=((args[0]<<32)|args[1])>>args[3];self.clobber(value>>32);self.r[3]=g.u32(value)
  elif t==COLLISION:
   assert args[0]==ACTOR and args[2]==1
   index=(args[1]-g.read(self.memory,g.POINTER))//52;assert index in g.INDICES
   self.clobber(self.c.replies[g.INDICES.index(index)])
  else:
   assert t==AUDIO;assert self.calls[-1][0]==g.SOUND
   self.clobber(g.effect(self.memory,self.c,g.SOUND,self.calls[-1][1],self.counts[g.SOUND]))
def main():
 count=0;visits=set()
 for selection,seed,fast,limit,mode,phase in itertools.product(range(7),SEEDS,(0,1),(0x14,0x1B,0x20),(0,8),(0,8)):
  replies=tuple(0 if i==selection and index<=limit else 1 for i,index in enumerate(g.INDICES))
  first=next_seed(seed);second=next_seed(first);c=g.Case(replies=replies,randoms=(first&0xFFFFFFFF,second&0xFFFFFFFF),mode=mode,phase=phase);pair=[]
  for ws in g.streams():
   m=Connected(ws,c,seed,fast,limit).run();expected,calls,observations=g.reference(m.initial,c)
   selected=any(t==g.RNG for t,a in calls);g.put(expected,SEED,second if selected else seed,8)
   assert m.calls==calls and m.observations==observations,(c,'connected boundary')
   assert g.public(m.memory)==g.public(expected),(c,'connected memory')
   assert m.seeds==([seed,first]if selected else[])
   audio=[a for t,a in m.leaves if t==AUDIO];sounds=[a for t,a in calls if t==g.SOUND]
   assert audio==[(0,*a)for a in sounds],(audio,sounds)
   pair.append(g.state(m));visits.update(m.visits)
  assert pair[0]==pair[1];count+=1
 coverage={hex(t):sum(t+4*i in visits for i in range(n))for t,_,n in PROVIDERS}
 assert coverage[hex(g.RNG)]==18 and coverage[hex(g.QUERY)]==73 and coverage[hex(g.SOUND)]==29,coverage
 r=dict(cases_per_stream=count,streams=2,provider_executed_words=coverage,current_provider_bytes_equal=True,
  independent_64bit_seed_reference=True,two_seed_transitions_checked=True,all_eleven_forwarded_sound_words=True,
  query_fast_mask_and_collision_paths=True,query_bounds_checked=True,setup_current_is_stub=True,
  setup_and_shift_collision_audio_leaf_internals_contracted=True,source_installed=packet.installed(),matching_credit=0)
 (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
