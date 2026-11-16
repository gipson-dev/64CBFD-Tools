"""Actual dispatcher, render slot6, vertex cache allocator and both buffer pages."""
from dataclasses import replace
from pathlib import Path
import hashlib,importlib.util,itertools,json,struct,sys
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_ribbon_renderer_151a3be4_oracle as g
O=g.O;R=g.R
DISPATCH,TRANSFORM,ALLOCATE,RELEASE,MARK=0x15147C4C,0x151462C8,0x10003C40,0x1516972C,0xC0000
ROM=(R/'conker/conker.us.bin').read_bytes();ELF=(R/'conker/build/conker.us.elf').read_bytes()
HASHES={name:hashlib.sha256((R/name).read_bytes()).hexdigest()for name in('conker/conker.us.bin','conker/build/conker.us.elf')}

def original(entry,n):
 at=entry-0x15000000+0x2D4B0;raw=ROM[at:at+4*n];off=elf_slot_offset(ELF,entry,4*n);assert ELF[off:off+4*n]==raw
 return list(struct.unpack('>%dI'%n,raw))

ALLOCATOR=original(g.BACKEND,52);PARENT=original(DISPATCH,52)
copy_at=elf_slot_offset(ELF,g.COPY,44);assert ELF[copy_at:copy_at+44]==ROM[0x22EC0:0x22EEC]
MEMCPY=list(struct.unpack('>11I',ROM[0x22EC0:0x22EEC]))

class Machine(g.Machine):
 def __init__(self,words,m,c,success,parent):
  self.alloc_success=success;self.forwarded=[];self.transforms=[];self.allocations=[];self.releases=[]
  code=dict(zip(range(g.BACKEND,g.BACKEND+208,4),ALLOCATOR));code.update(zip(range(g.COPY,g.COPY+44,4),MEMCPY))
  if parent:
   code.update(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));entry=DISPATCH;body=PARENT;args=(g.OUT-8,g.E,c.view)
  else:entry=g.ENTRY;body=words;args=(g.E,g.OUT,c.view)
  g.base.Machine.__init__(self,body,m,c,connected=code,entry=entry,args=args);self.cached_p=g.read(m,g.E+0x98)
 def record_call(self,t):
  if t==TRANSFORM:self.transforms.append(tuple(self.arguments(9)));return
  if t==g.ENTRY:self.forwarded.append(tuple(self.arguments(3)));return
  if t==ALLOCATE:self.allocations.append(tuple(self.arguments(4)));return
  if t==RELEASE:self.releases.append(tuple(self.arguments(1)));return
  return super().record_call(t)
 def hook(self,t):
  if t not in(TRANSFORM,ALLOCATE,RELEASE):return super().hook(t)
  value=g.OUT if t==TRANSFORM else g.V if t==ALLOCATE and self.alloc_success else 0
  if t==RELEASE:g.put(self.memory,MARK,0x13579BDF)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value

def main():
 streams=g.programs(['v7']);table=ROM[0x22ED64:0x22EDB0];table_va=g.S['D_8008A2A4'];at=elf_slot_offset(ELF,table_va,len(table))
 assert ELF[at:at+len(table)]==table and struct.unpack_from('>I',table,24)[0]==g.ENTRY
 count=0;allocator_seen=set();parent_seen=set();copy_seen=set();routes=set()
 for view,success,existing,flip,parent,flags,n,selector,seed in itertools.product((0,3,0xFFFF,0x12340002),(0,1),(0,1),(0,1),(0,1),(0,2,0x20,0x22),(1,3),(0,6,19),(0,10)):
  if not parent and selector!=6:continue
  size=5*32+160;accepted=bool(success or existing)
  c=g.Case(view=view,flags=flags,count=n,seed=seed,vertex_offset=0 if flip else size)
  m=g.fixture(c);slot=g.E+0x84+g.half(view)*4;g.put(m,slot,g.V if existing else 0);m[0x800BE9C0]=flip;g.put(m,MARK,0);m[g.E+0x31]=selector
  for i,value in enumerate(table):m[table_va+i]=value
  child=not parent or selector==6;body_reached=child and n>=2
  if child:expected,result,calls,segments=g.reference(m,replace(c,success=int(accepted)))
  else:expected,result,calls=dict(m),g.OUT,[]
  if body_reached and not existing:g.put(expected,slot,g.V if success else 0)
  if parent and selector>=19:g.put(expected,MARK,0x13579BDF);routes.add('release-invalid-selector')
  elif parent and selector==0:routes.add('bypass-zero-selector')
  elif n<2:routes.add('count-gate')
  elif accepted:routes.add('render')
  else:routes.add('allocation-failed')
  for label,words in streams.items():
   q=Machine(words,m,c,success,parent).run()
   assert(g.public(q.memory),q.r[2],q.calls)==(g.public(expected),result,calls),(label,c,success,existing,flip,parent,selector,'connected transfer')
   assert q.allocations==([(size*2,1,2,1)]if body_reached and not existing else[]),q.allocations
   assert q.releases==([(g.E,)]if parent and selector>=19 else[]),q.releases
   if parent:
    assert q.forwarded==([(g.E,g.OUT,g.u32(g.half(view)))]if selector==6 else[]),q.forwarded
    extra=g.read(m,g.E+0x28)if flags&0x20 else 0
    assert q.transforms==[(g.OUT-8,g.E+0x34,0,0,0,g.u32(g.half(view)),g.E+0x54,2,extra)],q.transforms
   allocator_seen.update(pc for pc in q.visits if g.BACKEND<=pc<g.BACKEND+208);parent_seen.update(pc for pc in q.visits if DISPATCH<=pc<DISPATCH+208)
   copy_seen.update(pc for pc in q.visits if g.COPY<=pc<g.COPY+44)
  count+=1
 assert len(copy_seen)==11,(len(copy_seen),sorted(hex(pc-g.COPY)for pc in copy_seen))
 assert len(allocator_seen)==52 and len(parent_seen)==52,(len(allocator_seen),len(parent_seen))
 for name,h in HASHES.items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h,name
 report=dict(cases_per_stream=count,streams=len(streams),original_memcpy_words=11,memcpy_words_visited=len(copy_seen),original_allocator_words=52,allocator_words_visited=len(allocator_seen),original_dispatcher_words=52,dispatcher_words_visited=len(parent_seen),slot='D_8008A2A4[6]',pointer_VA='0x8008A2BC',pointer_ROM='0x22ED7C',signed_view_and_return_propagation=True,cache_existing_failure_and_both_pages=True,routes=sorted(routes),transform_release_and_deep_allocator='bounded hooks',graphics_services='opaque matching ABI hooks',source_installed=False,c_match_credit=0)
 (O/'callers-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

if __name__=='__main__':main()
