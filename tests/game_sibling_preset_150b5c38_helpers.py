"""Replay original helpers using packets captured from the new preset."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import itertools,json,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.tests import game_sibling_preset_150b5c38_guest as g
from tools.tests import game_composite_preset_150b5a3c_helpers as old
from tools.tests import game_random_particle_150b5e34_guest as particle
from tools.tests import game_random_particle_150b5e34_helpers as factory
from tools.experiments import game_sibling_preset_150b5c38_match as p
r,o=p.ROOT,p.OUT
class Capture(g.Machine):
 def hook(self,t):
  if t==g.SUBMIT:self.composite_input=(dict(self.memory),self.calls[-1][1])
  if t==g.OTHER:self.particle_input=(dict(self.memory),self.calls[-1][1])
  if t==g.TAIL:self.tail_input=(dict(self.memory),self.calls[-1][1])
  super().hook(t)
class Particle(particle.Machine):
 def hook(self,t):
  if t==particle.FACTORY:self.factory_input=(dict(self.memory),self.calls[-1][1])
  super().hook(t)
def main():
 with patch.multiple(old,g=g,o=o,r=r,Capture=Capture),patch.object(old.p,'installed',lambda:False):composite_tail=old.main()
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();body,body_pin=factory.pin(g.OTHER,115,rom,elf);fw,fp=factory.pin(particle.FACTORY,61,rom,elf);cw,cp=factory.pin(factory.COPY,11,rom,elf)
 count=copied=0;visited=set();factory_visited=set();copy_visited=set()
 for rng,parity,outcome,mode,mutation,rm in itertools.product((0,0xffffffff),(0,3),(0,1),(0,255),(0,15),(0,3)):
  c=g.Case(mode=mode,extra=g.u32(rng^parity),mutation=mutation,phase=8*(mode&1),seed=parity,rm=rm);capture=Capture(g.programs()[0],c).run();memory,args=capture.particle_input
  hc=particle.Case(rng=(rng,parity&1,(parity>>1)&1),sample=particle.bits(.3),mode=args[1],extra=args[2],phase=c.phase-144,seed=c.seed,outcome=outcome,fcsr=c.rm|0x100,point=args[0],coords=tuple(g.read(memory,args[0]+4*i)for i in range(3)))
  m=Particle(body,replace(hc,phase=c.phase),memory=memory,args=args);m.c=m.case=hc;m.memory=dict(memory);m.r[29]=m.before[29]=particle.home(hc)
  for i,v in enumerate(args):g.put(m.memory,particle.home(hc)+4*i,v)
  m.initial=dict(m.memory);m.run();expected,calls,obs,fcsr,value=particle.reference(m.initial,hc)
  assert m.calls==calls and m.observations==obs and particle.public(m.memory,hc)==particle.public(expected,hc)and particle.data(m.memory,particle.packet(hc),112)==particle.data(expected,particle.packet(hc),112)
  assert m.fcsr==fcsr and m.r[2]==value and m.r[29]==particle.home(hc)and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
  memory,args=m.factory_input;fm=factory.Factory(fw,cw,replace(hc,phase=c.phase),memory,args);fm.c=fm.case=hc;fm.memory=dict(memory);fm.r[29]=fm.before[29]=fm.target_home=particle.home(hc)-152
  for i,v in enumerate(args[4:],4):g.put(fm.memory,fm.target_home+4*i,v)
  fm.initial=dict(fm.memory);fm.run();factory.verify(fm,hc,memory,args)
  visited.update(p for p in m.visits if g.OTHER<=p<g.OTHER+460);factory_visited.update(p for p in fm.visits if particle.FACTORY<=p<particle.FACTORY+244);copy_visited.update(p for p in fm.visits if factory.COPY<=p<factory.COPY+44);count+=1;copied+=outcome
 assert visited==set(range(g.OTHER,g.OTHER+460,4))and len(factory_visited)==41 and len(copy_visited)==11
 q=dict(composite_and_tail=composite_tail,particle=body_pin,factory=fp,memcpy=cp,particle_cases=count,particle_all115_words_visited=True,factory_actual_kind1_path_words_visited=41,memcpy_all11_words_visited=True,successful112_byte_copies=copied,particle_packet_bytes=112,particle_known_bytes=98,particle_seeded_holes=14,original_particle_two_FP_operations_checked=True,composite_tail_and_factory_allocator_internals_contracted=True,no_composite_tail_or_factory_FCSR_claim=True,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0)
 (o/'helpers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='composite_and_tail'}),flush=True)
 return q
if __name__=='__main__':main()
