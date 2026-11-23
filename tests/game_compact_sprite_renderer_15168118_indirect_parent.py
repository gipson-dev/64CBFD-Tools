"""Complete retail render-list parent connected to all three leaf streams.

The parent's current false C placeholder is unchanged and uncredited.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,struct,subprocess,sys
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_renderer_15168118_guest as g
PARENT=0x151674F8;RANGE=0x15168F84;BEFORE=0x15601000;AFTER=0x15601100
DESC=g.SYMS['D_8008B4A8'];HEADS=g.SYMS['D_800DCE50'];DEPTH=g.SYMS['D_800DD190'];ITER=g.SYMS['D_800DD198'];SELECTOR=0x12345678
@dataclass(frozen=True)
class Case(g.Case):
 row:int=0
 shape:int=2
 draw_mode:int=0
 stages:bool=False
 budget:int=1000
 clear_next:bool=False
 start:int=5
 stop:int=67
 viewport:int=0
def fixture(c):
 m=g.fixture(c);g.put(m,g.SYMS['D_800D2C9C'],0x40000)
 for i in range(0x2000):m[g.OUTPUT+i]=(i*13+7)&255
 at=g.elf_slot_offset(g.elf,DESC,104*52);data=g.elf[at:at+104*52]
 for i,b in enumerate(data):m[DESC+i]=b
 for i in range(2*104):g.put(m,HEADS+4*i,0)
 m[DEPTH]=0
 for i in range(8):g.put(m,ITER+4*i,0xCC000000+i)
 for i in range(4):g.put(m,g.SYMS['D_800BE9C8']+4*i,g.OUTPUT)
 m[g.SYMS['D_800BE9C0']]=c.viewport;g.put(m,g.SYMS['D_800BEBA4'],c.budget);g.put(m,g.SYMS['D_8003C8E0'],0);m[g.SYMS['D_800D2DAB']]=0
 # All cache fields used by the complete parent are mapped; the parent
 # deliberately writes its own retail sentinels before dispatching a column.
 for i in range(0x80):m[g.SYMS['D_800DD1B0']+i]=0xA5
 nodes={};original=bytes(m[g.STATE+i]for i in range(76))
 for k,column in enumerate((5,66)):
  descriptor=DESC+column*52;assert g.get(m,descriptor+8)==g.ENTRY
  g.put(m,descriptor+0x10,0x80123400+column*8 if c.stages else 0)
  g.put(m,descriptor+0x14,BEFORE if c.stages else 0);g.put(m,descriptor+0x20,AFTER if c.stages else 0)
  g.put(m,descriptor+0x24,0x80123500+column*8 if c.stages else 0);m[descriptor+0x30]=c.draw_mode&255
  count=0 if c.shape==0 else(1 if k==0 else 0)if c.shape==1 else 1 if c.shape==2 else 2
  chain=[g.STATE+(k*2+i)*0x100 for i in range(count)];nodes[column]=chain
  for i,p in enumerate(chain):
   for off,b in enumerate(original):m[p+off]=b
   g.put(m,p+8,chain[i+1]if i+1<len(chain)else 0)
   g.put(m,p+0x20,-32768+k*17+i,2);g.put(m,p+0x22,19+k*23+i,2)
  g.put(m,HEADS+c.row*0x1A0+column*4,chain[0]if chain else 0)
 return m,nodes
class Parent(g.Oracle):
 def __init__(self,words,leaf,memory,c,nodes):
  super().__init__(words,memory,c,entry=PARENT,connected={g.ENTRY+4*i:w for i,w in enumerate(leaf)},arguments=(g.OUTPUT,SELECTOR,g.u32(c.view),c.row))
  self.nodes=nodes;self.allowed={p for chain in nodes.values()for p in chain};self.active=None;self.parent_events=[];self.called_targets=[];self.range_calls=0
 def record_call(self,t):
  if t==g.ENTRY:
   a=tuple(map(g.u32,self.arguments(3)));assert a[1]in self.allowed and a[2]==g.u32(g.s16(self.case.view)),('Bad indirect renderer args',a)
   assert g.OUTPUT<=a[0]<g.OUTPUT+0x2000 and a[0]&7==0,a
   self.active=a[1];self.called_targets.append(a);return
  if t in(RANGE,BEFORE,AFTER):
   n=3 if t in(RANGE,AFTER)else 4;a=tuple(map(g.u32,self.arguments(n)));self.parent_events.append((t,a))
   if t==RANGE:
    assert a==(SELECTOR,g.u32(self.r[29]+0x88),g.u32(self.r[29]+0x84));self.range_calls+=1
   elif t==BEFORE:assert a[1]in(5,66)and a[2]==self.case.row and a[3]==g.u32(g.s16(self.case.view)),a
   else:assert a[1]in(5,66)and a[2]==g.u32(g.s16(self.case.view)),a
   return
  super().record_call(t)
 def hook(self,t):
  if t==RANGE:
   a=self.parent_events[-1][1];g.put(self.memory,a[1],self.case.start);g.put(self.memory,a[2],self.case.stop);value=0xDEADBEEF
  elif t in(BEFORE,AFTER):
   a=self.parent_events[-1][1];g.put(self.memory,a[0],0xAA000000|(t==AFTER));g.put(self.memory,a[0]+4,a[1]);value=a[0]+8
  else:
   name=g.NAME[t];a=self.calls[-1][1]
   value=g.contract(self.memory,self.case,name,a,self.packet,self.sync,state=self.active)
   if name=='func_15142E24'and self.case.clear_next:g.put(self.memory,self.active+8,0)
  for i in range(4):g.put(self.memory,self.r[29]+i*4,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=g.u32(value)
def state(m):return(g.public(m.memory),m.observations,m.parent_events,m.called_targets,m.r[2])
def rows():
 cases=[Case(row=row,shape=shape,draw_mode=mode,stages=stage,budget=budget)for row,shape,mode,stage,budget in itertools.product((0,1),(0,1,2,3),(0,1,2),(False,True),(3,1000))]
 cases +=[Case(row=row,shape=3,draw_mode=mode,clear_next=True,view=view,effect=7,viewport=3,phase=8)for row,mode,view in itertools.product((0,1),(0,1,2),(0,1,0xFFFF))]
 cases +=[Case(start=5,stop=5),Case(start=66,stop=67,shape=3,stages=True)]
 return cases
def main():
 raw_parent=(Path.cwd()/'conker/conker.us.bin').read_bytes()[0x1949A8:0x194F18];assert len(raw_parent)==1392
 source='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(o/'additional-baseline/conker/asm/nonmatchings/game_1944C0/func_151674F8.s').read_text();source+='\n.size func_151674F8,.-func_151674F8\n'
 asm=o/'original-parent.s';obj=o/'original-parent.o';asm.write_text(source)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(Path.cwd()/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 original_object=g.payload(obj,'func_151674F8');assert bytes().join(w.to_bytes(4,'big')for w in g.bound_blob(*original_object,g.SYMS))==raw_parent
 rom=(Path.cwd()/'conker/conker.us.bin').read_bytes();private=(o/'image-qualification/linked.elf').read_bytes()
 for index,rom_offset in((5,0x230074),(66,0x230CD8)):
  assert int.from_bytes(rom[rom_offset:rom_offset+4],'big')==g.ENTRY
  at=g.elf_slot_offset(private,DESC+index*52+8,4);assert int.from_bytes(private[at:at+4],'big')==g.ENTRY
 for image in(g.elf,private):
  slot=[v for _,n,v,_ in g.symbol_rows(image)if n=='func_151674F8'];assert len(slot)==1 and slot[0][1:3]==(PARENT,12)
 parent=list(struct.unpack('>348I',raw_parent));paths={'raw':o/'selected-v2/candidate.o','padded':o/'qualified-owner/game_1944C0.c.o','retail':o/'original-target.o'}
 leaves={name:g.bound_blob(*g.payload(path,'func_15168118'),g.SYMS)for name,path in paths.items()}
 caller_sites=set();coverage=set();counts={name:0 for name in paths};cases=rows()
 for c in cases:
  memory,nodes=fixture(c);models={name:Parent(parent,leaf,memory,c,nodes).run()for name,leaf in leaves.items()};truth=models['retail']
  assert truth.range_calls==1 and truth.memory[DEPTH]==0,c
  if c.budget==1000:
   expected=[p for col,chain in nodes.items()if c.start<=col<c.stop for p in chain]
   assert [a[1]for a in truth.called_targets]==expected,(c,truth.called_targets,expected)
  elif c.shape and c.start<c.stop:assert truth.called_targets,c
  for name,m in models.items():
   assert state(m)==state(truth),(name,c)
   counts[name]+=len(m.called_targets);coverage.update(m.visits)
  caller_sites.update(pc for pc in(0x151677F8,0x151678B0)if pc in truth.visits)
 assert caller_sites=={0x151677F8,0x151678B0}
 c=Case(shape=3,stages=True,clear_next=True);memory,nodes=fixture(c);truth=Parent(parent,leaves['retail'],memory,c,nodes).run();controls=[]
 wrong_memory=dict(memory);g.put(wrong_memory,DESC+5*52+8,0)
 wrong=Parent(parent,leaves['raw'],wrong_memory,c,nodes).run();assert state(wrong)!=state(truth);controls.append('missing-actual-registration')
 bad=parent[:]
 for va in(0x151677FC,0x151678B4):i=(va-PARENT)//4;assert bad[i]>>26==0x2B;bad[i]&=~(31<<16)
 wrong=Parent(bad,leaves['raw'],memory,c,nodes).run();assert state(wrong)!=state(truth);controls.append('lost-retained-next-in-delay-slot')
 bad=parent[:]
 for va in(0x151677F4,0x151678AC):i=(va-PARENT)//4;assert bad[i]==0x02002825;bad[i]=0x02802825
 try:Parent(bad,leaves['raw'],memory,c,nodes).run()
 except AssertionError as e:assert'Bad indirect renderer args'in str(e)
 else:raise AssertionError('Wrong descriptor argument survived')
 controls.append('descriptor-passed-instead-of-node')
 report=dict(parent='func_151674F8',parent_words=348,parent_frame=144,cases_per_stream=len(cases),streams={name:dict(renderer_invocations=n)for name,n in counts.items()},both_slot8_call_sites=[hex(p)for p in sorted(caller_sites)],actual_descriptor_columns=[5,66],effective_controls=controls,full_original_parent_executed=True,frozen_parent_assembly_independently_matches_ROM=True,actual_ROM_and_private_ELF_registrations_checked=True,current_false_C_parent_unchanged_and_uncredited=True,unexecuted_parent_words=[i for i in range(348)if PARENT+4*i not in coverage],limits='Complete original parent and complete leaf; range selection, pre/post callbacks and graphics providers are bounded contracts. Current parent C remains its unchanged false placeholder; no parent or gameplay credit.',source_installed=packet.installed(),matching_credit=0)
 (o/'indirect-parent.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
