"""Complete direct caller, retained state argument and negative owner control."""
from pathlib import Path
import itertools,json,struct
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
from tools.tests import game_compact_sprite_renderer_15168118_guest as g
r,o=packet.ROOT,packet.OUT
def main():
 q=o/'selected-v2';entry=0x15178750
 truth=list(struct.unpack('>21I',(packet.ROOT/'conker/conker.us.bin').read_bytes()[0x1A5C00:0x1A5C54]))
 caller=g.bound_blob(*g.payload(q/'caller.o','func_15178750'),g.SYMS)
 bad=g.bound_blob(*g.payload(q/'wrong-record.o','func_15178750'),g.SYMS)
 raw=g.bound_blob(*g.payload(o/'selected-v2/candidate.o','func_15168118'),g.SYMS)
 retail=list(struct.unpack('>337I',(packet.ROOT/'conker/conker.us.bin').read_bytes()[0x1955C8:0x195B0C]))
 assert caller==truth
 rows=[(g.Case(flags=f,view=v,width=-2000,height=-500,yaw=123,pitch=-30,effect=e,phase=p),mask)
  for f,v,e,p,mask in itertools.product((0,1,0x100,0x300),(0,1,7,8,31,32,0xFFFF),(0,7),(0,8),(0,1,0x80,0xFF))]
 report={}
 for label,words,target in(('original',truth,retail),('source',caller,raw)):
  count=0
  for c,mask in rows:
   memory=g.fixture(c);g.put(memory,g.SYMS['D_800D2C9C'],0x40000)
   parent=g.get(memory,g.STATE+0x14);g.put(memory,parent+0x36,mask,1)
   visible=bool(mask&(1<<(g.s16(c.view)&31)))
   if visible:want,log,result=g.reference(memory,c)
   else:want,log,result=memory,[],g.OUTPUT
   m=g.Oracle(words,memory,c,entry=entry,connected={g.ENTRY+4*i:w for i,w in enumerate(target)});m.run()
   assert(m.observations,m.r[2],g.public(m.memory))==(log,result,g.public(want)),(label,c,mask)
   assert len(m.target_calls)==int(visible)
   count+=int(visible)
  report[label]=dict(cases=len(rows),renderer_invocations=count)
 c=g.Case();memory=g.fixture(c);g.put(memory,g.SYMS['D_800D2C9C'],0x40000);g.put(memory,g.get(memory,g.STATE+0x14)+0x36,0xFF,1)
 try:g.Oracle(bad,memory,c,entry=entry,connected={g.ENTRY+4*i:w for i,w in enumerate(raw)}).run()
 except AssertionError as e:assert'Wrong renderer arguments'in str(e)
 else:raise AssertionError('Wrong parent pointer control survived')
 r=dict(streams=report,wrong_parent_pointer_control_effective=True,positive_caller_all_21_words_direct_from_C=True,limits='Complete direct caller and renderer, bounded graphics provider contracts. Signed view shifts outside 0..31 are guest extensions.',source_installed=packet.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
