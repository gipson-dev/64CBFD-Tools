"""Original composite loop and trailing random-position helper on real inputs."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import hashlib,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()));
from tools.tests import game_composite_preset_150b5a3c_guest as g
from tools.tests import game_composite_effect_factory_oracle as composite
from tools.tests import game_random_position_packet_oracle as tail
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_composite_preset_150b5a3c_match as p
r,o=p.ROOT,p.OUT
def pin(a,n,rom,elf):
 blob=rom[a-0x15000000+0x2d4b0:a-0x15000000+0x2d4b0+4*n];at=elf_slot_offset(elf,a,len(blob));assert elf[at:at+len(blob)]==blob;return list(struct.unpack('>'+str(n)+'I',blob)),dict(address=hex(a),words=n,sha256=hashlib.sha256(blob).hexdigest(),matches_frozen_ELF=True)
class Capture(g.Machine):
 def hook(self,t):
  if t==g.SUBMIT:self.composite_input=(dict(self.memory),self.calls[-1][1])
  if t==g.TAIL:self.tail_input=(dict(self.memory),self.calls[-1][1])
  super().hook(t)
class Tail(tail.Oracle):
 def record_call(self,t):
  super().record_call(t)
  if t==tail.SYMS['func_151602C0']:
   a=self.calls[-1][1];self.full_header_and_coords=(g.data(self.memory,a[0],6),g.data(self.memory,a[1],12))
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();cw,cp=pin(g.SUBMIT,270,rom,elf);tw,tp=pin(g.TAIL,56,rom,elf);cases=emits=0;cv=set();tv=set();bounds=[]
 rngs=(0,1,0x80000000,0xffffffff)
 for first,second,mode,mutation,phase in itertools.product(rngs,rngs,(0,255),(0,15),(0,8)):
  c=g.Case(mode=mode,extra=g.u32(first^second),mutation=mutation,phase=phase,seed=first&3);capture=Capture(g.programs()[-1],c).run();memory,a=capture.composite_input
  memory.update({g.MARK+i:memory.get(g.MARK+i,0xa5)for i in range(64)})
  hc=composite.Case(seed=(first^second)&3,mode=a[1],extra=a[2],mutation=0,phase=c.phase-144)
  with patch.multiple(composite,INPUT=a[0],MARK=g.MARK):
   expected,calls,payloads,ni,nf=composite.reference(memory,hc);m=composite.Machine(cw,memory,replace(hc,phase=c.phase));m.case=hc;m.home=m.r[29]=m.before[29]=g.home(c)-144;m.before_f=m.f[:];m.run()
   assert m.calls==calls and m.payloads==payloads and m.rng_i==ni and m.rng_f==nf
   assert g.public(m.memory,c)==g.public(expected,c);assert g.data(m.memory,a[0],116)==g.data(memory,a[0],116),'Composite input changed'
   assert m.r[29]==g.home(c)-144 and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   cv.update(pc for pc in m.visits if g.SUBMIT<=pc<g.SUBMIT+1080);emits+=m.submits
  memory,a=capture.tail_input;tc=tail.Case(random0=first,random1=second,kind=a[1],mode=a[2],pattern=0,mutation=0,phase=c.phase-144,position=a[0]);m=Tail(tw,memory,replace(tc,phase=c.phase));m.case=tc;m.target_home=m.r[29]=m.before[29]=g.home(c)-144;m.before_f=m.f[:];m.run();expected,calls,packet=tail.reference(memory,tc,ra=m.before[31]);assert m.calls==calls and m.packet_observations==[packet]
  header=g.STACK+tc.phase-8;coords=g.STACK+tc.phase-20;assert m.full_header_and_coords==(g.data(expected,header,6),g.data(expected,coords,12))
  assert g.public(m.memory,c)==g.public(expected,c);assert m.r[29]==g.home(c)-144 and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];tv.update(pc for pc in m.visits if g.TAIL<=pc<g.TAIL+224);cases+=1
 traps={g.SUBMIT+4*i for i,w in enumerate(cw)if w&0xfc00003f==13};assert len(traps)==14 and cv==set(range(g.SUBMIT,g.SUBMIT+1080,4))-traps and not(cv&traps);assert tv==set(range(g.TAIL,g.TAIL+224,4))
 q=dict(original_helpers=[cp,tp],cases_per_helper=cases,original_composite_words=270,visited_composite_nontrap_words=256,unreachable_divisor_traps=14,composite_child_emissions=emits,original_trailing_words_visited=56,complete_source_packet_bytes=116,composite_header_extent=24,composite_payload_extent=60,complete_trailing_header_bytes=6,trailing_coordinate_bytes=12,opaque_RNG_and_vector_and_allocation_providers=True,no_helper_FCSR_claim=True,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0)
 (o/'helpers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
