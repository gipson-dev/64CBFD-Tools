"""Connect original 64-bit RNG helpers; effect submission stays modeled."""
import json,struct
from dataclasses import replace
from tools.experiments import game_actor_random_particle_150de12c_match as p
from tools.tests import game_actor_random_particle_150de12c_guest as g
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED,SCALE=0x800885B0,0x8009F740
class Connected(g.Oracle):
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;inside=0x150ADA20<=self.current_pc<0x150ADACC
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
  elif op==17 and rs==20 and fn==32:
   v=self.f[rd];self.f[sh]=g.bits(float(v if v<0x80000000 else v-0x100000000))
  else:
   before=self.r[:];super().execute(w)
   if inside:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,v in enumerate(before):
     if i!=dest and v>0xFFFFFFFF:self.r[i]=v
  self.r[0]=0
 def hook(self,t):
  assert t==g.SUBMIT
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=0x87654321
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();code={}
 for entry,offset,n in ((g.RAND_FLOAT,0xDAF18,25),(g.RAND_INT,0xDAED0,18)):code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
 raw,refs=p.payload(p.out/'qualified-source/candidate.o');lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});count=0;visited=set()
 for seed in SEEDS:
  seeds=[];v=seed
  for _ in range(5):v=next_seed(v);seeds.append(v)
  sample=g.bits(g.rounded(float(seeds[0]&65535)*g.floating(0x37800080)));c=g.Case(random_float=sample,choice=seeds[1]&0xFFFFFFFF,first=seeds[2]&0xFFFFFFFF,second=seeds[3]&0xFFFFFFFF,third=seeds[4]&0xFFFFFFFF)
  m=Connected(words,c,connected=code);g.put(m.memory,SEED,seed,8);g.put(m.memory,SCALE,0x37800080);m.initial=dict(m.memory);expected,args=g.reference(m.initial,c);g.put(expected,SEED,seeds[-1],8);m.run();public=lambda x:{a:v for a,v in x.items()if not g.STACK-512<=a<g.STACK+512}
  assert public(m.memory)==public(expected);assert m.calls[-1][1][1:]==args and m.obs==list(g.descriptor(c))and m.r[2]==1;visited.update(pc for pc in m.visits if g.RAND_INT<=pc<g.RAND_FLOAT+100);count+=1
 r=dict(cases=count,original_rng_words=43,visited_rng_words=len(visited),five_seed_transitions_checked=True,submission_still_modeled=True,source_installed=p.installed());(p.out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
