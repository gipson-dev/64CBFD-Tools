"""Original gate, RNGs, sampler path3, factory and memcpy; allocation/zero leaves modeled."""
from pathlib import Path
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_particle_emission_accumulator_150ec520_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_particle_emission_accumulator_150ec520_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED=0x800885B0;FACTOR=0x8009F740;VIEW_COUNT=0x80082FA0;ALLOCATE=0x15167A68;ZERO=0x100226F0
PROVIDERS=((g.GATE_FN,0x173968,20),(g.FRNG,0xDAF18,25),(g.RNG,0xDAED0,18),(g.SAMPLE,0x17076C,254),(g.FACTORY,0x1765E0,49),(g.COPY,0x22EC0,11))
@lru_cache(maxsize=1)
def inputs():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
 for t,off,n in PROVIDERS:
  blob=rom[off:off+4*n]
  if t!=g.SAMPLE:assert elf[elf_slot_offset(elf,t,4*n):elf_slot_offset(elf,t,4*n)+4*n]==blob
  code.update(zip(range(t,t+4*n,4),struct.unpack('>%dI'%n,blob)))
 at=elf_slot_offset(elf,FACTOR,4);factor=struct.unpack_from('>I',elf,at)[0];assert factor==0x37800080
 return code,factor
class Connected(g.Oracle):
 def __init__(self,words,c,seed,view_count,mask):
  code,factor=inputs();super().__init__(words,c,connected=code);self.seeds=[];self.leaves=[]
  g.put(self.memory,SEED,seed,8);g.put(self.memory,FACTOR,factor);g.put(self.memory,VIEW_COUNT,view_count);g.put(self.memory,g.GATE+2,mask,2);self.initial=dict(self.memory)
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;inside=g.RNG<=self.current_pc<g.RNG+72 or g.FRNG<=self.current_pc<g.FRNG+100
  if op in(55,63):
   prior=self.own_instruction;self.own_instruction=True
   try:
    a=g.u32(self.r[rs]+((w&65535)^32768)-32768);assert a%8==0
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
  if t in(ALLOCATE,ZERO):
   self.leaves.append((t,tuple(map(g.u32,self.arguments(6 if t==ALLOCATE else 2)))));return
  super().record_call(t)
  if t in(g.RNG,g.FRNG):self.seeds.append(g.read(self.memory,SEED,8))
 def hook(self,t):
  if t==ALLOCATE:
   ordinal=self.counts[g.FACTORY];args=self.calls[-1][1];assert self.calls[-1][0]==g.FACTORY
   assert self.leaves[-1][1]==(35,args[8],56,1,args[7],1)
   if self.c.mode&16:g.put(self.memory,g.packet_address(self.home),g.bits(float(-ordinal)));self.memory[g.RECORD+0xC]=(self.c.kind+ordinal)&255
   self.clobber(g.OUTPUT+64*(ordinal-1)if self.c.allocation_mask&(1<<(ordinal-1))else 0)
  else:
   assert t==ZERO;a,n=self.leaves[-1][1];assert n==16
   for i in range(n):self.memory[a+i]=0
   self.clobber(0)
def main():
 code,factor=inputs();count=0;visits=set();sampler_visits=set()
 for seed,accum,view_count,mask,allocation,phase,rm in itertools.product(SEEDS,(0.,2.25),(-1,0,3),(0,1,8),(0,0x55,0xFF),(0,8),range(4)):
  effective=(1<<(view_count+1))-1 if view_count>=0 else 0;gate=int(mask&effective==0)
  first=next_seed(seed);draw,flags=g.fp.arithmetic(g.bits(float(first&65535)),factor,2,rm);v=first;randoms=[]
  for _ in range(8):v=next_seed(v);randoms.append(v&0xFFFFFFFF)
  c=g.Case(accumulator=g.bits(accum),gate_result=gate,random_float=draw,randoms=tuple(randoms),allocation_mask=allocation,phase=phase,fcsr=rm,rng_flags=flags,sample_flags=0);pair=[]
  for ws in g.streams():
   m=Connected(ws,c,seed,view_count,mask).run();expected,calls,obs,fcsr=g.reference(m.initial,c)
   draws=sum(t in(g.FRNG,g.RNG)for t,a in calls);seeds=[];v=seed
   for _ in range(draws):seeds.append(v);v=next_seed(v)
   g.put(expected,SEED,v,8)
   assert m.calls==calls and m.observations==obs,(c,'connected boundary')
   assert g.public(m.memory)==g.public(expected),(c,'connected memory')
   assert m.fcsr==fcsr and m.seeds==seeds,(c,'FCSR/seed')
   pair.append(g.state(m));visits.update(m.visits)
  assert pair[0]==pair[1];count+=1
 coverage={hex(t):sum(t+4*i in visits for i in range(n))for t,_,n in PROVIDERS}
 for t,n in((g.GATE_FN,20),(g.FRNG,25),(g.RNG,18),(g.COPY,11)):assert coverage[hex(t)]==n,coverage
 r=dict(cases_per_stream=count,streams=2,provider_executed_words=coverage,current_sampler_is_stub=True,
  original_sampler_path=3,other_sampler_paths_unqualified=True,independent_64bit_seed_reference=True,
  factory_byte_count_and_narrow_fields=True,allocation_and_zero_leaf_internals_contracted=True,
  source_installed=packet.installed(),matching_credit=0)
 (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
