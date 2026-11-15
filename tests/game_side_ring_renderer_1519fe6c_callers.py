"""Complete original graphics dispatcher and vertex allocator integration."""
from dataclasses import replace
from pathlib import Path
import itertools,json,struct
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
R,O=g.R,g.O
DISPATCH,TRANSFORM,ALLOCATE=0x15147C4C,0x151462C8,0x10003C40

def original(entry,n):
 rom=(R/'conker/conker.us.bin').read_bytes();raw=rom[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+4*n]
 elf=(R/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,entry,len(raw));assert elf[at:at+len(raw)]==raw
 return list(struct.unpack('>'+str(n)+'I',raw))
class Machine(g.Machine):
 def __init__(self,w,m,c,success,existing,flip,parent):
  self.alloc_success=success;self.existing=existing;self.flip=flip;self.parent=parent;self.forwarded=[];self.transforms=[];self.allocations=[]
  code=dict(zip(range(g.BACKEND,g.BACKEND+208,4),original(g.BACKEND,52)))
  if parent:
   code.update(zip(range(g.ENTRY,g.ENTRY+4*len(w),4),w));super().__init__(original(DISPATCH,52),m,c,connected=code,entry=DISPATCH,args=(g.OUT-8,g.E,c.view))
  else:super().__init__(w,m,c,connected=code)
 def record_call(self,t):
  if t==TRANSFORM:self.transforms.append(tuple(self.arguments(9)));return
  if t==g.ENTRY:self.forwarded.append(tuple(self.arguments(3)));return
  if t==ALLOCATE:self.allocations.append(tuple(self.arguments(4)));return
  return super().record_call(t)
 def hook(self,t):
  if t not in(TRANSFORM,ALLOCATE):return super().hook(t)
  value=g.OUT if t==TRANSFORM else g.V if self.alloc_success else 0
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value

def main():
 p=g.programs();count=0;allocator_visits=set();parent_visits=set()
 rom=(R/'conker/conker.us.bin').read_bytes();table=rom[0x22ED64:0x22EDB0];elf=(R/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,g.S['D_8008A2A4'],len(table))
 assert elf[at:at+len(table)]==table and struct.unpack_from('>I',table,20)[0]==g.ENTRY
 for view,success,existing,flip,parent,flags in itertools.product((0,3,0xFFFF,0x12340002),(0,1),(0,1),(0,1),(0,1),(0,2)):
  c=g.Case(view=view,flags=flags);m=g.fixture(c);slot=g.E+0x84+g.half(view)*4
  g.put(m,slot,g.V if existing else 0);m[0x800BE9C0]=flip
  for i,v in enumerate(table):m[g.S['D_8008A2A4']+i]=v
  size=c.cap*48+0x120;accepted=success or existing
  expected,result,calls,segments=g.reference(m,replace(c,success=int(accepted)))
  if not existing:g.put(expected,slot,g.V if success else 0)
  # The original backend selects the second buffer when the page byte is zero.
  # Shift only newly emitted vertices and the corresponding VTX command pointers.
  if accepted and not flip:
   generated=bytes(expected[g.V+i] for i in range(segments*48+48))
   for i in range(2048):expected[g.V+i]=m[g.V+i]
   for i,v in enumerate(generated):expected[g.V+size+i]=v
   for command in range(g.OUT,result,8):
    if g.read(expected,command)==0x0100600C:g.put(expected,command+4,g.read(expected,command+4)+size)
  for label,w in p.items():
   q=Machine(w,m,c,success,existing,flip,parent).run()
   assert (g.public(q.memory),q.r[2],q.calls)==(g.public(expected),result,calls),(label,c,success,existing,flip,parent,'connected transfer')
   want_alloc=[] if existing else [(size*2,1,2,1)];assert q.allocations==want_alloc
   if parent:
    assert q.forwarded==[(g.E,g.OUT,g.u32(g.half(view)))]
    assert q.transforms==[(g.OUT-8,g.E+0x34,0,0,0,g.u32(g.half(view)),g.E+0x54,2,0)]
   allocator_visits|={pc for pc in q.visits if g.BACKEND<=pc<g.BACKEND+208}
   parent_visits|={pc for pc in q.visits if DISPATCH<=pc<DISPATCH+208}
  count+=1
 report=dict(cases_per_stream=count,streams=len(p),original_allocator_words=52,allocator_visited_words=len(allocator_visits),original_dispatcher_words=52,dispatcher_visited_words=len(parent_visits),render_table='D_8008A2A4',slot=5,signed_view_and_return_propagation=True,vertex_cache_and_page_selection=True,deep_allocator_and_graphics_services='bounded hooks',c_match_credit=0)
 assert len(allocator_visits)==52
 (O/'connected-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
