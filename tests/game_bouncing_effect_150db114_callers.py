"""Complete original status callback dispatcher on bounded lifecycle paths."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_bouncing_effect_150db114_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_bouncing_effect_150db114_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;PARENT=0x1513CFE4;TABLE=0x80089CB8;TIMER=0x800BE9E4;FREE=0x1516972C
@lru_cache(maxsize=1)
def rom():return(r/'conker/conker.us.bin').read_bytes()
def original():
 path=o/'baseline/conker/asm/nonmatchings/game_169510/func_1513CFE4.s';rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',path.read_text());blob=bytes.fromhex(''.join(w for _,_,w in rows));old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,PARENT,len(blob));assert len(rows)==195 and blob==rom()[0x16A494:0x16A7A0]==old[at:at+len(blob)];return[int(w,16)for _,_,w in rows]
def fixture(c,active,selector,flags,life,delta):
 m=g.fixture(c);table=rom()[0x22E778:0x22E820];assert len(table)==168 and struct.unpack_from('>I',table,9*4)[0]==g.ENTRY
 old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,TABLE,168);assert table==old[at:at+168];m.update({TABLE+i:v for i,v in enumerate(table)})
 for off,value,n in((0x10,active,4),(0x58,flags,4),(0x1C,life&65535,2),(0x24,0,4),(0x70,selector,1),(0x71,0,1),(0x72,0,1)):g.put(m,c.object+off,value,n)
 g.put(m,TIMER,delta&0xFFFFFFFF);return m
class ReturnCode(dict):
 def __getitem__(self,pc):
  if pc==PARENT+0x7C and self.owner.pending is not None:self.owner.child_return()
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,active,selector,flags,life,delta,poison=None,invert=False):
  m=fixture(c,active,selector,flags,life,delta);super().__init__(parent,c,memory=m,entry=PARENT,arguments=(c.object,),connected=dict(zip(range(g.ENTRY,g.ENTRY+452,4),leaf)));self.outer=c;self.pending=None;self.child_checks=0;self.post_calls=[];self.expected_child=int(bool(active&1)and selector==9);self.expected_free=bool(active&1)and(bool(flags&1)and (((life-delta)&65535)^32768)-32768<0 or selector==9 and c.alpha<c.fade);self.poison=poison;self.code=ReturnCode(self.code);self.code.owner=self
  if invert:self.code[0x1513D064]=0x10400002
 def record_call(self,t):
  if t==g.ENTRY:
   assert tuple(self.arguments(1))==(self.outer.object,);self.c=replace(self.outer,phase=self.outer.phase-32);self.pending=(g.reference(self.memory,self.c,self.fcsr),len(self.fp_operations));return
  assert t==FREE,hex(t);self.post_calls.append((t,tuple(self.arguments(1))))
 def child_return(self):
  want,ops=self.pending;assert(got:=(self.memory,self.fp_operations[ops:],self.fcsr,self.r[2]))==want,dict(components=[a==b for a,b in zip(got,want)]);self.pending=None;self.child_checks+=1;self.c=self.outer
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  assert t==FREE
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA6000000+i
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011
 def verify(self):
  assert self.pending is None and self.child_checks==self.expected_child
  assert self.post_calls==([(FREE,(self.outer.object,))]if self.expected_free else[]),(self.outer,self.expected_free,self.post_calls)
  assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent=original();leaves=[g.bound_blob(*g.payload(o/f,'func_150DB114'),g.symbols(g.Case()))for f in('original-target.o','selected-owner.o')];count=children=0
 for active,selector,flags,life,delta,(a,f),y,rm in itertools.product((0,1),(0,9),(0,1),(-32768,-1,0,1,32767),(-1,0,1,0x80000000),((0,0),(0,1),(128,128),(255,1)),(.5,2.),range(4)):
  c=g.Case(alpha=a,fade=f,y=g.bits(y),rm=rm,phase=8*(rm&1));models=[Connected(parent,leaf,c,active,selector,flags,life,delta).run().verify()for leaf in leaves];assert g.state(models[0])==g.state(models[1])and models[0].post_calls==models[1].post_calls;count+=1;children+=models[0].child_checks
 controls=[]
 for name,c,kw in(('expired-return-poison',g.Case(alpha=0,fade=1),dict(poison=1)),('live-return-poison',g.Case(alpha=128,fade=1),dict(poison=0)),('inverted-consumer',g.Case(alpha=0,fade=1),dict(invert=True))):
  base=Connected(parent,leaves[0],c,1,9,0,1,1).run().verify();bad=Connected(parent,leaves[0],c,1,9,0,1,1,**kw).run();assert bad.pending is None and bad.child_checks==1 and bad.post_calls!=base.post_calls;controls.append(dict(name=name,complete_parent_execution=True,rejected=True))
 q=dict(parent_words_pinned=195,parent_frame=32,table_bytes_pinned=168,table_selector=9,cases_per_stream=count,connected_children_per_stream=children,streams=2,complete_original_parent_on_qualified_paths=True,status_return_controls_expiration=True,unsigned_selector_and_lifetime_wrap_qualified=True,child_full_memory_FP_HILO_and_saved_ABI_equal=True,other_callbacks_fade_modes_and_texture_animation_not_qualified=True,opaque_free_provider_not_gameplay=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
