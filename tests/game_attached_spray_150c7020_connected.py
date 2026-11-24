"""Original integer RNG execution through the four ordered 64-bit seed updates."""
from dataclasses import replace
import itertools,json,struct
from tools.experiments import game_attached_spray_150c7020_match as p
from tools.tests import game_attached_spray_150c7020_guest as g
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED=0x800885b0
class Connected(g.Oracle):
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;inside=g.RNG<=self.current_pc<g.RNG+72
  if op in(55,63):
   prior=self.own_instruction;self.own_instruction=True
   try:
    a=(self.r[rs]+((w&65535)^32768)-32768)&0xffffffff;assert a%8==0
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
   a,b=self.r[rs]&0xffffffff,self.r[rt]&0xffffffff;assert b;self.lo,self.hi=a//b,a%b
  else:
   before=self.r[:];super().execute(w)
   if inside:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,v in enumerate(before):
     if i!=dest and v>0xffffffff:self.r[i]=v
  self.r[0]=0
 def record_call(self,t):
  super().record_call(t)
  if t==g.RNG:self.seed_observations.append(g.read(self.memory,SEED,8))
 def hook(self,t):assert t in(g.PREPARE,g.SUBMIT);super().hook(t)
def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();blob=rom[0xdaed0:0xdaf18];elf=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();at=p.elf_slot_offset(elf,g.RNG,72);assert elf[at:at+72]==blob;code=dict(zip(range(g.RNG,g.RNG+72,4),struct.unpack('>18I',blob)));count=0;visits=set()
 def make(ws,c,seed,selected=code):
  m=Connected(ws,c,connected=selected);g.put(m.memory,SEED,seed,8);m.initial=dict(m.memory);m.seed_observations=[];return m
 for seed,phase,life,mode in itertools.product(SEEDS,(0,8),(0,1,-32768),(0,1,4,5)):
  values=[];v=seed;seeds=[]
  for _ in range(4):seeds.append(v);v=next_seed(v);values.append(v&0xffffffff)
  c=g.Case(phase=phase,lifetime=life,mode=mode,rng=tuple(values));states=[]
  for ws in g.streams():
   m=make(ws,c,seed);m.run();wanted,calls,obs=g.reference(m.initial,c);g.put(wanted,SEED,v,8);assert(g.public(m.memory,c),m.calls,m.observations,m.seed_observations)==(g.public(wanted,c),calls,obs,seeds);states.append(g.state(m));visits.update(m.visits)
  assert all(v==states[0]for v in states);count+=1
 assert sum(g.RNG+4*i in visits for i in range(18))==18
 seed=0x123456789abcdef0;v=seed;values=[]
 for _ in range(4):v=next_seed(v);values.append(v&0xffffffff)
 c=g.Case(rng=tuple(values));bad=dict(code);assert bad[g.RNG+60]==0x0004103c;bad[g.RNG+60]=0x0004107c;m=make(g.streams()[0],c,seed,bad);m.run();_,calls,obs=g.reference(m.initial,c);assert(m.calls,m.observations)!=(calls,obs)
 q=dict(cases_per_stream=count,streams=4,integer_RNG_words_executed=18,seed_transitions_per_case=4,independent_seed_reference=True,effective_wrong_RNG_shift_control=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'connected.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
