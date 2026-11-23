"""Measured per-origin operands and results; no binary rewriting or credit."""
from pathlib import Path
from collections import defaultdict
from dataclasses import replace
import inspect,json,struct,sys,textwrap
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_renderer_15168118_guest as g
ENTRY=g.ENTRY
run_text=textwrap.dedent(inspect.getsource(g.TriangleOracle.run))
run_text=run_text.replace('if take is not None:\n','if take is not None:\n            self.branch_event(pc, word, take)\n')
run_text=run_text.replace('self.execute(self.code[pc + 4])','self.at(pc + 4)').replace('self.execute(word)','self.at(pc)')
assert run_text.count('self.at(pc + 4)')==3 and run_text.count('self.at(pc)')==1
namespace=dict(g.TriangleOracle.run.__globals__);exec(run_text,namespace)
class Trace(g.Oracle):
 run=namespace['run']
 def __init__(self,words,memory,c,source):
  super().__init__(words,memory,c);self.source=source;self.origin_events=defaultdict(list);self.pointer_regs={29:'frame'}
 def canon(self,v):
  v=g.u32(v)
  if not self.source:return v
  base=g.STACK+self.case.phase-168;off=g.u32(v-base)
  if 144<=off<164:return g.u32(v+4)
  return g.u32(base+{143:139,142:86,141:87}[off])if off in(143,142,141)else v
 def branch_event(self,pc,w,take):
  op=w>>26;rs=w>>21&31;rt=w>>16&31
  C=lambda reg:self.canon(self.r[reg])if self.pointer_regs.get(reg)=='local'else self.r[reg]
  if op==17:values=(self.condition,)
  elif op in(4,5,20,21):values=tuple(sorted((C(rs),C(rt))))
  else:values=(C(rs),)
  self.origin_events[(pc-ENTRY)//4].append(('branch',values,take))
 def at(self,pc):
  w=self.code[pc];i=(pc-ENTRY)//4;op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;shift=w>>6&31;fn=w&63;imm=w&65535;off=(imm^32768)-32768
  r=self.r[:];f=self.f[:];condition=self.condition;tags=dict(self.pointer_regs)
  self.execute(w);C=self.canon
  # Track pointer provenance. Arbitrary mode words can numerically equal a
  # private stack address; such integers must never be relocated by observation.
  dest=None;tag=None
  if op==9:
   dest=rt
   if rs==29:
    if rt==29:tag='frame'
    else:
     offset=g.u32(self.r[rt]-(g.STACK+self.case.phase-168))
     if(141<=offset<164 if self.source else offset in(86,87,139)or 148<=offset<168):tag='local'
   elif tags.get(rs)=='local':tag='local'
  elif op in(10,11,12,13,14,15,0x20,0x21,0x23,0x24,0x25):dest=rt
  elif op==0:
   dest=rd
   if fn==37 and(rs==0 or rt==0):tag=tags.get(rs or rt)
  elif op==17 and rs==0:dest=rt
  if dest is not None:
   self.pointer_regs.pop(dest,None)
   if tag:self.pointer_regs[dest]=tag
  before=lambda reg:C(r[reg])if tags.get(reg)=='local'else r[reg]
  after=lambda reg:C(self.r[reg])if self.pointer_regs.get(reg)=='local'else self.r[reg]
  if w==0:event=('nop',)
  elif op in(0x20,0x21,0x23,0x24,0x25):event=('load',op,C(r[rs]+off),after(rt))
  elif op in(0x28,0x29,0x2B):
   size={0x28:1,0x29:2,0x2B:4}[op];value=r[rt]&((1<<(size*8))-1)
   event=('store',op,C(r[rs]+off),before(rt)if size==4 else value)
  elif op==0x31:event=('float-load',C(r[rs]+off),self.f[rt])
  elif op==0x39:event=('float-store',C(r[rs]+off),f[rt])
  elif op==15:event=('lui',after(rt))
  elif op==9:
   event=('stack-address',after(rt))if rs==29 else('add-immediate',before(rs),off,after(rt))
  elif op in(10,11,12,13,14):event=('immediate',op,before(rs),imm,after(rt))
  elif op==0:
   if fn==37 and(rs==0 or rt==0):event=('move',before(rs or rt),after(rd))
   elif fn in(0,2,3):event=('shift',fn,before(rt),shift,after(rd))
   elif fn in(33,37,36,38):event=('alu',fn,tuple(sorted((before(rs),before(rt)))),after(rd))
   elif fn in(35,42,43):event=('alu',fn,(before(rs),before(rt)),after(rd))
   else:raise AssertionError(('Unexpected source ALU',i,hex(w)))
  elif op==17:
   if rs==4:event=('to-float',r[rt],self.f[rd])
   elif rs==0:event=('from-float',f[rd],self.r[rt])
   elif rs==20 and fn==32:event=('convert-int-float',f[rd],self.f[shift])
   elif rs==16:
    if fn in(0,2):event=('float',fn,tuple(sorted((f[rd],f[rt]))),self.f[shift])
    elif fn==1:event=('float',fn,(f[rd],f[rt]),self.f[shift])
    elif fn in(5,6,13):event=('float',fn,f[rd],self.f[shift])
    elif fn in(50,60,62):event=('compare',fn,(f[rd],f[rt]),self.condition)
    else:raise AssertionError(('Unexpected FPU source',i,hex(w)))
   else:raise AssertionError(('Unexpected COP1 transfer',i,hex(w)))
  else:raise AssertionError(('Unobserved instruction family',i,hex(w)))
  self.origin_events[i].append(event)
 def hook(self,t):
  super().hook(t)
  for reg in(1,2,3,*range(4,16),24,25):self.pointer_regs.pop(reg,None)
def words():
 a=g.bound_blob(*g.payload(o/'selected-v2/candidate.o','func_15168118'),g.SYMS)
 b=g.bound_blob(*g.payload(o/'original-target.o','func_15168118'),g.SYMS)
 return a,b
def main():
 proposal=json.loads((packet.TOOLROOT/'experiments/game_compact_sprite_renderer_15168118_role_plan.json').read_text())
 order=proposal['order'];raw,retail=words();rows=g.cases();diffs=[];seen_a=set();seen_b=set();speculative=0
 # The flag-mask load moves into a normal branch delay slot. On the false
 # path it reads a byte initialized at entry and its temporary dies at the
 # constant definition before any use. It is not full access-trace identity.
 assert raw[7]==0xA3A0009D and raw[19]==0x93B9009D
 assert raw[18]>>26==4 and raw[18]&65535==3 and raw[28]==0x24190100
 for number,c in enumerate(rows):
  memory=g.fixture(c);g.put(memory,g.SYMS['D_800D2C9C'],0x40000)
  a=Trace(raw,memory,c,True).run();b=Trace(retail,memory,c,False).run();seen_a.update(a.origin_events);seen_b.update(b.origin_events)
  for j,i in enumerate(order):
   if a.origin_events[i]==b.origin_events[j]:continue
   if(i,j)==(19,20)and not c.flags&8 and len(a.origin_events[i])==1 and not b.origin_events[j]:speculative+=1;continue
   diffs.append(dict(case=number,retail=j,raw=i,raw_events=a.origin_events[i][:3],retail_events=b.origin_events[j][:3]))
  if diffs:break
 report=dict(cases=number+1,requested_cases=len(rows),different_origins=diffs,source_unexecuted=[i for i in range(len(raw))if i not in seen_a],retail_unexecuted=[i for i in range(len(retail))if i not in seen_b],omitted_copies=[193,218,241,263],private_dead_load_instances=speculative,qualification='Measured trace only; no guards or code rewriting',source_installed=packet.installed(),matching_credit=0)
 (o/('origin-trace-all.json'if len(rows)>1 else'origin-trace-initial.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
