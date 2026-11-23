"""Complete original constructor chain and original render-list parent/renderer."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_indexed_matrix_renderer_15168c4c_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_indexed_matrix_renderer_15168c4c_guest as q
g=q.g;PARENT=0x151674F8;RANGE=0x15168F84;CTOR=0x15168BE4;ALLOCATE=0x10003C6C;NEW=0x15167A68;INSERT=0x15168A4C
DESC=g.SYMS['D_8008B4A8'];HEADS=g.SYMS['D_800DCE50'];DEPTH=g.SYMS['D_800DD190'];ITER=g.SYMS['D_800DD198'];TEMPLATE=q.STATE+0x1000;EXISTING=q.STATE+0x800
elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();symbols={n:v for _,n,v,_ in g.symbol_rows(elf)if n};COPY=symbols['bcopy'][1]
def mapped(names):return{symbols[n][1]+i*4:w for n in names for i,w in enumerate(q.words(n))}
def scene(c):
 m=q.fixture(c);at=g.elf_slot_offset(elf,DESC,101*52)
 for i,b in enumerate(elf[at:at+101*52]):m[DESC+i]=b
 for i in range(208):g.put(m,HEADS+i*4,0)
 for i in range(128):m[g.SYMS['D_800DD1B0']+i]=0xA5
 m[DEPTH]=0
 for i in range(6):g.put(m,ITER+i*4,0xCC000000+i)
 for i in range(2):g.put(m,g.SYMS['D_800BE9C8']+i*4,q.OUTPUT)
 g.put(m,g.SYMS['D_800BEBA4'],1000);g.put(m,g.SYMS['D_8003C8E0'],0);m[g.SYMS['D_800D2DAB']]=0
 return m
class Constructor(q.Oracle):
 def __init__(self,m,c,flags,context,outcome,mutate):
  super().__init__(q.words('func_15168BE4'),m,c,entry=CTOR,connected=mapped(('func_15167A68','func_15168A4C')),arguments=(TEMPLATE,flags,context));self.flags=flags;self.context=context;self.outcome=outcome;self.mutate=mutate;self.constructor_calls=[];self.copy_bytes=[]
 def record_call(self,t):
  counts={NEW:6,INSERT:2,ALLOCATE:5,COPY:3};assert t in counts,hex(t);a=tuple(map(g.u32,self.arguments(counts[t])));self.constructor_calls.append((t,a))
  if t==NEW:assert a==(16,self.context,240,1,self.flags&255,1),a
  if t==INSERT:assert a==(q.STATE,16),a
  if t==ALLOCATE:assert a==(240,1,1,0,1),a
  if t==COPY:assert a==(TEMPLATE,q.STATE+0x90,96),a;self.copy_bytes.append(bytes(self.memory[TEMPLATE+i]for i in range(96)))
 def hook(self,t):
  if t==ALLOCATE:
   if self.mutate:self.memory[TEMPLATE+0x55]^=0x55;self.memory[TEMPLATE+0x5C]=(self.memory[TEMPLATE+0x5C]+1)%3
   self.clobber(q.STATE if self.outcome else 0);return
  assert t==COPY;a=self.constructor_calls[-1][1];data=bytes(self.memory[a[0]+i]for i in range(a[2]))
  for i,b in enumerate(data):self.memory[a[1]+i]=b
  self.clobber()
def constructor_cases():return list(itertools.product((0,1,2),(0,1),(0,255),(0,1),(False,True),(False,True),(False,True)))
def constructor_main():
 total=draws=0;coverage=set();native_domain=set();guest_residue_modes=set()
 for mode,row,flags,outcome,asset,existing,mutate in constructor_cases():
  c=q.Case(mode=mode,combine=int(mode!=0),alpha=255,tile=37,pattern=mode,home_word=0x80ABCDEF);memory=scene(c);context=0xABCD0000|row;flags_word=0x12340000|flags
  for i in range(96):memory[TEMPLATE+i]=memory[q.STATE+0x90+i]
  g.put(memory,TEMPLATE+0x40,0x80123400 if asset else 0)
  for i in range(16):memory[EXISTING+i]=0xA5
  slot=HEADS+row*0x1A0+16*4;g.put(memory,slot,EXISTING if existing else 0)
  expected=dict(memory)
  if asset:
   if mutate:expected[TEMPLATE+0x55]^=0x55;expected[TEMPLATE+0x5C]=(expected[TEMPLATE+0x5C]+1)%3
   if outcome:
    expected[q.STATE+1]=row;expected[q.STATE]=16;g.put(expected,q.STATE+8,EXISTING if existing else 0);g.put(expected,q.STATE+4,0)
    if existing:g.put(expected,EXISTING+4,q.STATE)
    g.put(expected,slot,q.STATE);expected[q.STATE+12]=flags
    for i in range(96):expected[q.STATE+0x90+i]=expected[TEMPLATE+i]
  m=Constructor(memory,c,flags_word,context,outcome,mutate).run();assert g.public(m.memory)==g.public(expected),(mode,row,flags,outcome,asset,existing,mutate);coverage.update(m.visits)
  assert len(m.copy_bytes)==int(asset and outcome);assert sum(t==ALLOCATE for t,a in m.constructor_calls)==int(asset)
  if asset and outcome:
   actual_mode=m.memory[q.STATE+0xEC];home=g.get(m.memory,q.STACK+c.phase-8);want,log,value=q.reference(m.memory,c,home_word=home)
   for obj in('selected-final/candidate.o','original-target.o'):
    ws=g.bound_blob(*g.payload(o/obj,'func_15168C4C'),g.SYMS);draw=q.Oracle(ws,m.memory,c).run();assert(g.public(draw.memory),draw.log,draw.r[2])==(g.public(want),log,value)
   draws+=1
   (native_domain if actual_mode in(1,2)else guest_residue_modes).add(actual_mode)
  total+=1
 assert native_domain=={1,2}and guest_residue_modes=={0}
 return dict(cases=total,constructed_then_drawn_cases=draws,complete_functions={'constructor':26,'allocator_wrapper':28,'list_insert':20},defined_native_modes=sorted(native_domain),actual_upstream_guest_residue_modes=sorted(guest_residue_modes),constructor_unexecuted=[i for i in range(26)if CTOR+i*4 not in coverage],limits='Complete26/28/20-word constructor/wrapper/inserter with bounded malloc and96-byte bcopy; all copied opaque bytes and live packet mutations compared; successful records connected to complete renderer/actual mode helper. No allocator or bcopy-internal execution claim.')
class Code(dict):
 def __init__(self,data,model):super().__init__(data);self.model=model
 def __getitem__(self,key):
  m=self.model
  if m.pending and key==m.pending[0]:
   _,expected,log,value,start=m.pending
   assert(g.public(m.memory),m.log[start:],m.r[2])==(g.public(expected),log,value),('Complete leaf return boundary',m.node_modes,m.log[start:],log)
   m.checked_returns+=1;m.pending=None
  return super().__getitem__(key)
class Parent(q.Oracle):
 def __init__(self,ws,m,c,row,node_modes,budget,parent_mode):
  code=mapped(('func_15168F84',));code.update({q.ENTRY+i*4:w for i,w in enumerate(ws)})
  super().__init__(q.words('func_151674F8'),m,c,entry=PARENT,connected=code,arguments=(q.OUTPUT,0,g.u32(c.view),row));self.row=row;self.node_modes=node_modes;self.pending=None;self.checked_returns=0;self.parent_calls=[];self.residues=[];self.code=Code(self.code,self)
 def record_call(self,t):
  if t==RANGE:
   a=tuple(map(g.u32,self.arguments(3)));assert a[0]==0;self.parent_calls.append((t,(0,'first','last')));return
  if t==q.ENTRY:
   a=tuple(map(g.u32,self.arguments(3)));assert a[1]in{q.STATE+i*0x200 for i in range(len(self.node_modes))}and a[2]==g.u32(g.s16(self.case.view)),a
   assert self.pending is None;self.active=a[1];home=g.get(self.memory,self.r[29]-8);expected,log,value=q.reference(self.memory,self.case,state=self.active,output=a[0],home_word=home)
   self.pending=(self.r[31],expected,log,value,len(self.log));self.residues.append(home);self.parent_calls.append((t,a));return
  super().record_call(t)
def parent_main():
 report={};parent_coverage=set();total=draws=0;carry=0
 cases=list(itertools.product((0,1),((),(1,),(2,),(0,),(2,0),(1,0),(0,2,0)),(0,1,2),(3,1000),(0,1),(0,1)))
 for row,modes,parent_mode,budget,combine,effect in cases:
  c=q.Case(mode=modes[0]if modes else 1,combine=combine,effect=effect,view=-1 if row else 0,home_word=0x80ABCDEF);initial=scene(c);g.put(initial,g.SYMS['D_800BEBA4'],budget);initial[DESC+16*52+0x30]=parent_mode
  base=bytes(initial[q.STATE+i]for i in range(240));nodes=[q.STATE+i*0x200 for i in range(len(modes))]
  for index,(node,mode)in enumerate(zip(nodes,modes)):
   for i,b in enumerate(base):initial[node+i]=b
   initial[node]=16;initial[node+1]=row;initial[node+0xEC]=mode;g.put(initial,node+8,nodes[index+1]if index+1<len(nodes)else 0)
  g.put(initial,HEADS+row*0x1A0+16*4,nodes[0]if nodes else 0);g.put(initial,q.STACK-144-8,c.home_word)
  models=[]
  for path in('selected-final/candidate.o','original-target.o'):
   ws=g.bound_blob(*g.payload(o/path,'func_15168C4C'),g.SYMS);m=Parent(ws,initial,c,row,modes,budget,parent_mode).run();assert m.pending is None and m.checked_returns==sum(t==q.ENTRY for t,a in m.parent_calls);models.append(m);parent_coverage.update(m.visits)
  a,b=models;assert(g.public(a.memory),a.log,a.parent_calls,a.r[2],a.residues)==(g.public(b.memory),b.log,b.parent_calls,b.r[2],b.residues)
  if modes==(2,0)and budget==1000:
   assert len(a.residues)==2 and a.residues[1]==0x504A50,('Lost private render-word carry',a.residues);carry+=1
  total+=1;draws+=a.checked_returns
 return dict(cases_per_stream=total,leaf_invocations_per_stream=draws,complete_parent_words=348,complete_range_helper_words=47,actual_descriptor_column=16,private_mode_two_to_zero_carry_cases=carry,all_leaf_return_boundaries_checked=True,parent_unexecuted=[i for i in range(348)if PARENT+i*4 not in parent_coverage],limits='Complete original/current348-word parent, actual47-word range and complete renderer/mode helper; matrix provider bounded. Real column16, rows0/1, zero/multiple nodes, three parent rollback modes and mode0 residue sequences. No native mode0/private-home claim.')
def main():
 report=dict(constructor=constructor_main(),parent=parent_main(),source_installed=packet.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
