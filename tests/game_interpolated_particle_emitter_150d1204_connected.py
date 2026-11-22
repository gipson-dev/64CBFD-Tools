"""Execute both original 64-bit RNG routines through all four seed transitions."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct,sys
from tools.experiments import game_interpolated_particle_emitter_150d1204_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_interpolated_particle_emitter_150d1204_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED=0x800885B0;FACTOR=0x8009F740
class Connected(g.Oracle):
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  inside=g.RNG<=self.current_pc<g.RNG+72 or g.FRNG<=self.current_pc<g.FRNG+100
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
  super().record_call(t)
  if t in(g.FRNG,g.RNG):self.seed_observations.append(g.read(self.memory,SEED,8))
 def hook(self,t):assert t==g.EMIT;super().hook(t)

def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
 for entry,offset,n in((g.RNG,0xDAED0,18),(g.FRNG,0xDAF18,25)):
  blob=rom[offset:offset+4*n];at=elf_slot_offset(elf,entry,4*n);assert elf[at:at+4*n]==blob
  code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,blob)))
 at=elf_slot_offset(elf,FACTOR,4);factor=struct.unpack_from('>I',elf,at)[0];assert factor==0x37800080
 def prepare(ws,c,seed,selected=code,scale=factor):
  m=Connected(ws,c,connected=selected);g.put(m.memory,SEED,seed,8);g.put(m.memory,FACTOR,scale)
  m.initial=dict(m.memory);m.seed_observations=[];return m
 count=0;visits=set()
 for seed,alias,phase,fraction,rm in itertools.product(SEEDS,range(3),(0,8),(0.,.1,1.),range(4)):
  values=[];v=seed;seeds=[]
  for _ in range(4):seeds.append(v);v=next_seed(v);values.append(v&0xFFFFFFFF)
  converted=[g.arithmetic(g.bits(float(x&65535)),factor,2,rm)for x in values[:2]]
  c=g.Case(alias=alias,phase=phase,fraction=g.bits(fraction),fcsr=rm,
           floats=tuple(v for v,f in converted),rng_flags=tuple(f for v,f in converted),integers=tuple(values[2:]));states=[]
  for ws in g.streams():
   m=prepare(ws,c,seed);m.run();expected,calls,observations,fcsr=g.reference(m.initial,c,connected=True);g.put(expected,SEED,v,8)
   assert m.calls==calls and g.public(m.memory)==g.public(expected),(seed,alias,phase,'state/calls')
   assert [o[:3]for o in m.observations]==[o[:3]for o in observations]
   assert m.fcsr==fcsr and m.seed_observations==seeds,(seed,'FCSR/seed transitions')
   states.append(g.state(m));visits.update(m.visits)
  assert states[0]==states[1];count+=1
 assert sum(g.RNG+4*i in visits for i in range(18))==18
 assert sum(g.FRNG+4*i in visits for i in range(25))==25
 seed=0x123456789ABCDEF0;v=seed;values=[]
 for _ in range(4):v=next_seed(v);values.append(v&0xFFFFFFFF)
 converted=[g.arithmetic(g.bits(float(x&65535)),factor,2,0)for x in values[:2]]
 c=g.Case(floats=tuple(v for v,f in converted),rng_flags=tuple(f for v,f in converted),integers=tuple(values[2:]))
 bad=dict(code);assert bad[g.RNG+60]==0x0004103C;bad[g.RNG+60]=0x0004107C
 controls=[]
 for label,selected,scale in(('wrong-integer-RNG-return-shift',bad,factor),('wrong-float-RNG-scale',code,g.bits(1./32768.))):
  m=prepare(g.streams()[0],c,seed,selected,scale);m.run();_,calls,_,_=g.reference(m.initial,c,connected=True)
  if m.calls==calls:
   print(json.dumps(dict(control=label,seed=seed,expected_integers=c.integers,actual_emission=m.calls[-1][1],seed_after=g.read(m.memory,SEED,8))),flush=True)
  assert m.calls!=calls,label;controls.append(label)
 r=dict(cases_per_stream=count,streams=2,integer_RNG_words_executed=18,float_RNG_words_executed=25,
        seed_transitions_per_case=4,float_RNG_coefficient_bits='0x37800080',independent_seed_reference=True,effective_controls=controls,
        emission_helper_internals_modeled=True,source_installed=packet.installed(),matching_credit=0)
 (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
