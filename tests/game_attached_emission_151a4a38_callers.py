"""Execute the complete original 45-word callback dispatcher around the recovery."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.tests import game_attached_emission_151a4a38_oracle as g
O=g.O
PARENT,TABLE,CLEAN_TABLE,CLEAN,RELEASE,TICKS=0x15149264,0x8008A4E8,0x8008A4C0,0x150AE790,0x1516972C,0x800BE9E4
ROM=(g.R/'conker/conker.us.bin').read_bytes();body=list(struct.unpack_from('>45I',ROM,0x176714))
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ELF=(g.R/'conker/build/conker.us.elf').read_bytes()
for address,raw in((PARENT,ROM[0x176714:0x1767C8]),(CLEAN_TABLE,ROM[0x22EF80:0x22EF84]),(TABLE+20,ROM[0x22EFBC:0x22EFC0])):
 at=elf_slot_offset(ELF,address,len(raw));assert ELF[at:at+len(raw)]==raw
assert int.from_bytes(ROM[0x22EF80:0x22EF84],'big')==CLEAN
class Machine(g.Machine):
 def __init__(self,words,m,c,revive):
  code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words))
  g.base.Machine.__init__(self,body,m,c,connected=code,entry=PARENT,args=(g.E,0,0,0));self.target_home=g.STACK+c.phase-24;self.ri=0;self.homes=[];self.output_home=None;self.callbacks=[];self.revive=revive
 def record_call(self,t):
  if t==g.ENTRY:self.callbacks.append(tuple(self.arguments(1)));return
  if t in(CLEAN,RELEASE):self.calls.append((t,tuple(self.arguments(1)),b''));self.raw_calls.append((t,tuple(self.arguments(1))));return
  super().record_call(t)
 def hook(self,t):
  if t not in(CLEAN,RELEASE):return super().hook(t)
  assert self.raw_calls[-1][1]==(g.E,)
  if t==CLEAN:g.put(self.memory,g.E+0xE,0 if self.revive else -1,2);self.memory[g.E+0xD]^=0x20
  else:g.put(self.memory,g.MARK,0x87654321);self.memory[g.E+0xD]^=0x80
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=0xCAFEBABE
def main(label='v13'):
 streams=g.programs(label);seen=set();n=0
 for route,flag,lifetime,selector,cleanup,revive,phase in itertools.product((0,1,3,6),(0,1),(-1,2,32767),(5,255),(0,255),(0,1),(0,8)):
  c=g.Case(seed=255 if revive else 0,flips=revive*3,route=route,mutation=31,phase=phase,pattern=3);initial=g.fixture(c)
  initial[g.E+0xD]=flag;initial[g.E+0x10]=cleanup;initial[g.E+0x11]=selector;g.put(initial,g.E+0xE,lifetime,2);g.put(initial,TICKS,3);g.put(initial,TABLE+20,g.ENTRY);g.put(initial,CLEAN_TABLE,CLEAN)
  expected=dict(initial);calls=[];callbacks=[]
  if flag:g.put(expected,g.E+0xE,g.half(lifetime-3),2)
  if selector==5:
   callbacks.append((g.E,));expected,calls,answer,ops=g.reference(expected,c,home=g.STACK+phase-24)
  if g.half(g.read(expected,g.E+0xE,2))<0 and cleanup==0:
   calls.append((CLEAN,(g.E,),b''));g.put(expected,g.E+0xE,0 if revive else -1,2);expected[g.E+0xD]^=0x20
  if g.half(g.read(expected,g.E+0xE,2))<0:
   calls.append((RELEASE,(g.E,),b''));g.put(expected,g.MARK,0x87654321);expected[g.E+0xD]^=0x80
  states=[]
  for name,words in streams.items():
   q=Machine(words,initial,c,revive).run();assert(g.public(q.memory),q.calls,q.callbacks)==(g.public(expected),calls,callbacks),(name,route,flag,lifetime,selector,cleanup,revive,phase,'original parent')
   seen.update(pc for pc in q.visits if PARENT<=pc<PARENT+180);states.append(q.fp_ops)
  assert all(v==states[0]for v in states[1:]),'parent FP order';n+=1
 assert len(seen)==45,len(seen)
 report=dict(cases_per_stream=n,streams=len(streams),original_parent_words=45,words_visited=45,entire_original_parent=True,argument_A0_owner_and_ignored_result=True,signed_callback_disable_and_lifetime_wrap=True,original_two_tables=True,post_cleanup_lifetime_recheck=True,cleanup_and_release_bounded_hooks=True,source_installed=False,c_match_credit=0)
 (O/'callers-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v13')
