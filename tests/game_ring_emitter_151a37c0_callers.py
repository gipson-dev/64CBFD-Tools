"""Original second callback table, return/release routes and real provider chain."""
from pathlib import Path
import importlib.util,json,struct,sys
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

from tools.tests import game_ring_emitter_151a37c0_oracle as g
OUT=g.source.OUT
PARENT,END,TABLE,RELEASE,MARK,TICK=0x15147740,0x151478D0,0x8008A23C,0x1516972C,0x90000,0x800BE9E4

class Parent(g.Machine):
 def record_call(self,target):
  if target not in(g.ENTRY,RELEASE):return super().record_call(target)
  args=tuple(self.arguments(1));assert args==(g.E,),(hex(target),args)
  self.calls.append((target,args))
 def hook(self,target):
  if target!=RELEASE:return super().hook(target)
  g.put(self.memory,MARK,0x13579BDF)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=0xDEADBEEF

def full_state(q):return q.r,q.f,q.hi,q.lo,q.memory,q.calls,q.fp_ops

def main():
 rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();elf=(g.source.ROOT/'conker/build/conker.us.elf').read_bytes()
 assert struct.unpack_from('>I',rom,0x22ED14)[0]==g.ENTRY
 assert struct.unpack_from('>I',elf,elf_slot_offset(elf,TABLE+24,4))[0]==g.ENTRY
 parent=list(struct.unpack_from('>100I',rom,0x174BF0));offset=elf_slot_offset(elf,PARENT,400)
 assert elf[offset:offset+400]==struct.pack('>100I',*parent)
 streams=g.programs();visited=set();routes=set();count=0
 corpus=[c for c in g.cases() if c.alias==0 and (c.hit==1 or not c.qeffects)][::17]
 for c in corpus:
  for connected in(False,True):
   for mode in range(3):
    initial=g.fixture(c);g.put(initial,TABLE+24,g.ENTRY);g.put(initial,MARK,0);g.put(initial,TICK,1)
    initial[g.E+0x2F]=0;initial[g.E+0x30]=6
    g.put(initial,g.E+0x1E,c.flags|(1 if mode else 0),2);g.put(initial,g.E+0x1C,0 if mode==1 else 32767,2)
    expected=dict(initial);remove=False
    if mode:
     timer=(g.read(expected,g.E+0x1C,2)-g.read(expected,TICK))&65535
     g.put(expected,g.E+0x1C,timer,2);remove=bool(timer&32768)
    calls=[];ops=[]
    if not remove:
     expected,answer,providers,ops=g.reference(c,expected,connected)
     calls=[(g.ENTRY,(g.E,))]+providers;remove=not answer
     routes.add('callback-zero'if not answer else'callback-one')
    else:routes.add('expired-parent')
    if remove:calls.append((RELEASE,(g.E,)));g.put(expected,MARK,0x13579BDF)
    exact={}
    for label,words in streams.items():
     q=Parent(words,c,initial,connected);q.snapshot-=32;q.r[31]=END
     code=g.helpers()if connected else{};code.update(zip(range(PARENT,END,4),parent));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code[END]=0
     q.code=WindowCode(code,q);q.code.ends=(END,);q.entry=PARENT
     try:q.run()
     except WindowBoundary:pass
     else:raise AssertionError('parent boundary not reached')
     assert q.calls==calls,(c,mode,connected,label,'calls',q.calls,calls)
     assert g.public(q.memory)==g.public(expected),(c,mode,connected,label,'public state')
     assert q.fp_ops==ops,(c,mode,connected,label,'ordered FP')
     assert q.r[29]==g.STACK+c.phase and q.r[31]==END and q.f[20:]==q.initial_fp[20:]
     assert all(q.r[i]==q.initial_regs[i]for i in(*range(16,24),28,30))
     if label in('retail','guarded'):exact[label]=full_state(q)
     visited.update(pc for pc in q.visits if PARENT<=pc<END)
    assert exact['retail']==exact['guarded'],(c,mode,connected,'literal parent state')
    count+=1
 assert routes=={'callback-zero','callback-one','expired-parent'},routes
 report=dict(cases_per_stream=count,caller='func_15147740',parent_words=100,parent_words_visited=len(visited),slot='D_8008A23C[6]',pointer_VA='0x8008A254',pointer_ROM='0x22ED14',parent_matches_retail=True,original_query_cleanup_memcpy_connected=True,return_zero_releases_and_one_keeps=True,release_is_opaque=True,routes=sorted(routes),raw_public_ABI_FP_agreement=True,guarded_complete_state_identity=True,source_installed=False,c_match_credit=0)
 (OUT/'callers-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':main()
