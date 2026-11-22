"""Execute the retained 64-bit RNG; player registration remains contracted."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct,sys
from tools.experiments import game_actor_trail_player_effect_15194810_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_actor_trail_player_effect_15194810_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED=0x800885B0
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
   left,right=self.r[rs]&0xFFFFFFFF,self.r[rt]&0xFFFFFFFF;assert right
   self.lo,self.hi=left//right,left%right
  else:
   before=self.r[:];super().execute(w)
   if inside:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,v in enumerate(before):
     if i!=dest and v>0xFFFFFFFF:self.r[i]=v
  self.r[0]=0
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 words=struct.unpack_from('>18I',rom,0xDAED0);a=elf_slot_offset(elf,g.RNG,72);assert elf[a:a+72]==struct.pack('>18I',*words)
 code=dict(zip(range(g.RNG,g.RNG+72,4),words));streams=g.programs();visited=set();count=0
 for seed,kind,mode,phase in itertools.product(SEEDS,(0,4,5,83,255),(0,1,2,15),(0,8)):
  value=next_seed(seed);c=g.Case(kind=kind,rng=value&0xFFFFFFFF,mode=mode,phase=phase,alias=mode&1)
  baseline=g.check(streams[1],c);expected=dict(baseline.memory)
  for i in range(4):expected[g.MARK+4+i]=baseline.initial[g.MARK+4+i]
  g.put(expected,SEED,value if kind<5 or kind==83 else seed,8);machines=[]
  for ws in streams:
   m=Connected(ws,c,connected=code);g.put(m.memory,SEED,seed,8);m.initial=dict(m.memory);m.run()
   assert g.public(m.memory)==g.public(expected),(seed,kind,mode,'public')
   assert m.calls==baseline.calls and m.obs==baseline.obs,(seed,kind,mode,'calls')
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:]
   machines.append(m);visited.update(m.visits)
  assert g.final_state(machines[0])==g.final_state(machines[1])==g.final_state(machines[2])
  assert g.normalized_trace(machines[0])==g.normalized_trace(machines[1])==g.normalized_trace(machines[2])
  count+=1
 assert {g.RNG+4*i for i in range(18)}<=visited
 r=dict(cases_per_stream=count,streams=3,original_rng_words=18,covered_rng_words=18,original_seed_transition_checked=True,unsigned32_remainder_after_signed64_return=True,remaining_providers_modeled=True,source_installed=packet.installed(),matching_credit=0)
 (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
