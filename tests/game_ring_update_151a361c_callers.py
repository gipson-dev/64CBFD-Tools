"""Actual table slot 6, callback-result window and bounded full parent paths."""
import json,struct
from tools.experiments import game_ring_update_151a361c_recovery as m
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_ring_update_151a361c_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
PARENT,END,TABLE,RELEASE,MARK=0x15147740,0x151478D0,0x8008A200,0x1516972C,0x90000

class Parent(g.Machine):
 def record_call(self,target):
  assert target in(g.ENTRY,RELEASE),('unbounded parent provider',hex(target));args=tuple(self.arguments(1));assert args==(g.OWNER,)
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==RELEASE;g.put(self.memory,MARK,0x13579BDF)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def main():
 m.check_inputs();rom=(m.FROZEN/'conker/conker.us.bin').read_bytes();elf=(m.ROOT/'conker/build/conker.us.elf').read_bytes();before=(m.FROZEN/'conker/build/conker.us.elf').read_bytes()
 assert struct.unpack_from('>I',rom,0x22ECD8)[0]==g.ENTRY
 assert struct.unpack_from('>I',elf,elf_slot_offset(elf,TABLE+24,4))[0]==g.ENTRY
 parent=list(struct.unpack_from('>100I',rom,0x174BF0));current=elf[elf_slot_offset(elf,PARENT,400):elf_slot_offset(elf,PARENT,400)+400]
 assert current==before[elf_slot_offset(before,PARENT,400):elf_slot_offset(before,PARENT,400)+400]
 streams=m.programs();visited=set();routes=set();count=0;corpus=g.native_cases()[::8]
 for c in corpus:
  for mode in range(3):
   initial=g.fixture(c);g.put(initial,TABLE+24,g.ENTRY);g.put(initial,MARK,0);initial[g.OWNER+0x2F]=6;initial[g.OWNER+0x30]=0
   g.put(initial,g.OWNER+0x1E,0 if mode==0 else 1,2);g.put(initial,g.OWNER+0x1C,0 if mode==1 else 32767,2)
   expected=dict(initial);remove=False
   if mode:
    timer=g.s16(g.read(expected,g.OWNER+0x1C,2)-g.read(expected,g.TICK));g.put(expected,g.OWNER+0x1C,timer,2);remove=timer<0
   calls=[]
   if not remove:
    expected,answer=g.reference(c,expected);calls.append((g.ENTRY,(g.OWNER,)));remove=not answer;routes.add('callback-zero'if not answer else'callback-one')
   else:routes.add('expired-parent')
   if remove:calls.append((RELEASE,(g.OWNER,)));g.put(expected,MARK,0x13579BDF)
   baseline=None
   for label,words in streams.items():
    q=Parent(words,c);q.memory=dict(initial);q.r[31]=END;code=dict(zip(range(PARENT,END,4),parent));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code[END]=0
    q.code=WindowCode(code,q);q.code.ends=(END,);q.entry=PARENT
    try:q.run()
    except WindowBoundary:pass
    else:raise AssertionError('parent boundary not reached')
    assert q.calls==calls,(c,mode,label,'callback/release',q.calls,calls)
    assert g.public(q.memory)==g.public(expected),(c,mode,label,'public state')
    assert q.r[29]==g.STACK+c.phase and q.r[31]==END and q.f[20:]==q.initial_fp[20:]
    observed=g.signature(q)
    if baseline is None:baseline=observed
    else:assert observed==baseline,(c,mode,label,'complete parent state')
    visited.update(pc for pc in q.visits if PARENT<=pc<END)
   count+=1
 assert routes=={'callback-zero','callback-one','expired-parent'},routes
 report=dict(cases_per_stream=count,caller='func_15147740',parent_words=100,parent_words_visited=len(visited),bounded_parent_paths=True,slot='D_8008A200[6]',pointer_VA='0x8008A218',pointer_ROM='0x22ECD8',parent_matches_retail=current==struct.pack('>100I',*parent),production_parent_unchanged=True,return_zero_releases_and_one_keeps=True,release_is_opaque=True,routes=sorted(routes),source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'callers.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
