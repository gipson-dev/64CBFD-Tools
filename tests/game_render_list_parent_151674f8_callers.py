"""All six complete callers and actual range helper connected to the parent."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_render_list_parent_151674f8_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_render_list_parent_151674f8_native as n
g,p=n.g,n.p
ROOTS=(0x15018E88,0x15018F08,0x150195A0,0x150198FC,0x15019BB8,0x15019CC8)
COLS=(5,66,80,89,93,97,100)
GROUPS={0:(1,65),1:(66,79),2:(80,88),3:(89,92),4:(93,96),5:(97,99),6:(100,101)}
COUNTS={0x1517D7B0:2,0x15174AA4:3,0x15174B48:3,0x1517EFAC:1,0x1510B7B4:2,0x1515D6D0:2,0x1510B958:1,0x1501A490:6,0x151135C4:3,0x151D6778:1,0x15186794:2,0x1502BAD0:3,0x15035FE8:2,0x15188D00:3,0x151D5E90:4,0x1501A680:1,0x151D61B0:1,0x1517E28C:2,0x15172F70:1,0x15181EE0:1,0x1517F564:1,0x1508FD38:1,0x15096934:1,0x1517F4D8:2,0x1517F3A0:2,0x15180580:2,0x1507DB6C:2}
@dataclass(frozen=True)
class Case:
 root:int=ROOTS[0]
 view:int=0
 pattern:int=0
 mode:int=0
 budget:int=1000
 stages:bool=False
 gate:int=0
 clear:bool=False
 phase:int=0
 cookie:int=0
 count:int=1
def cases():
 result=[Case(root,view,(view+mode)&1,mode,budget,stage)for root,view,mode,budget,stage in itertools.product(ROOTS,(0,1),(0,1,2),(3,1000),(False,True))]
 result +=[Case(ROOTS[2],view,gate=gate,phase=phase,stages=True)for view,gate,phase in itertools.product((0,1),(1,2,3,4),(0,8))]
 result +=[Case(ROOTS[3],view,gate=1,stages=True,cookie=cookie,count=count)for view,cookie,count in itertools.product((0,1),(0,1,4,5),(-1,0,1))]
 result +=[Case(ROOTS[4],view,gate=gate,stages=True)for view,gate in itertools.product((0,1),(0,2,4,6))]
 result +=[Case(root,view,stages=True,clear=True,phase=8)for root,view in itertools.product(ROOTS,(0,1))]
 return list(dict.fromkeys(result))
def fixture(c):
 base=n.Case(shape=3,draw_mode=c.mode,budget=c.budget,stages=c.stages,clear_next=c.clear,view=c.view,phase=c.phase)
 m,nodes=n.fixture(base)
 # Camera views and root gates occupy separate fields from the four small
 # record headers; both sets of bytes are retained in the complete fixture.
 for at in(0x30000,0x40000):
  for i in range(4*0x9A0):m.setdefault(at+i,0xA5)
  for i in range(4):g.put(m,at+i*0x9A0+0x5F0,c.pattern if at==0x30000 else c.pattern^1)
 for name,value,size in(('D_800DBFF0',0x30000,4),('D_800BEAC0',int(c.gate==1),1),('D_800BEAC1',int(c.gate==2),1),('D_80084480',int(c.gate==2),2),('D_800D18A0',(1<<c.view)if c.gate==4 else 0,2),('D_800D18A2',(1<<c.view)if c.gate==6 else 0,2),('D_80082FA0',c.count,4),('D_80082FA4',0,4),('D_800BE628',0x80401234,4),('D_800BE575',(c.pattern+c.mode)%3,1),('D_800BE616',c.pattern,1),('D_800BE9F0',0x1D if c.pattern else 0,4),('D_800BE620',320,4),('D_800BE624',240,4),('D_800BE9C4',0x80380000,4),('D_80082F90',c.cookie,1)):
  g.put(m,g.SYMS[name],value,size)
 for i in range(2):g.put(m,g.SYMS['D_800DC2A0']+i*4,0x81200000+i*0x1000)
 for i in range(-2,3):g.put(m,g.SYMS['D_8002AAEC']+i*4,0x803C0000+i*0x1000)
 for i in range(208):g.put(m,p.HEADS+4*i,0)
 for col in COLS:
  d=p.DESC+col*52;g.put(m,d+8,g.ENTRY);g.put(m,d+0x10,0x80123400+col*8 if c.stages else 0);g.put(m,d+0x14,p.BEFORE if c.stages else 0);g.put(m,d+0x20,p.AFTER if c.stages else 0);g.put(m,d+0x24,0x80123500+col*8 if c.stages else 0);m[d+0x30]=c.mode
  g.put(m,p.HEADS+col*4,g.STATE);g.put(m,p.HEADS+0x1A0+col*4,g.STATE+0x200)
 return m,{col:[g.STATE+i*0x100 for i in range(4)]for col in COLS},base
def function_words(name,elf):
 rows={n:v for _,n,v,_ in g.symbol_rows(elf)if n};row=rows[name];at=g.elf_slot_offset(elf,row[1],row[2]);return list(struct.unpack('>%dI'%(row[2]//4),elf[at:at+row[2]]))
class Model(n.Model):
 def __init__(self,c,m,nodes,base,parent,callers,range_words):
  connected={p.PARENT+i*4:w for i,w in enumerate(parent)}
  connected.update({p.RANGE+i*4:w for i,w in enumerate(range_words)})
  for entry,ws in callers.items():connected.update({entry+i*4:w for i,w in enumerate(ws)})
  g.Oracle.__init__(self,callers[c.root],m,base,entry=c.root,connected=connected,arguments=(g.OUTPUT,)if c.root==ROOTS[3]else(g.OUTPUT,c.view))
  self.nodes=nodes;self.allowed={g.STATE+i*0x100 for i in range(4)};self.active=None;self.parent_events=[];self.called_targets=[];self.range_calls=0;self.log=[];self.draw_id=0;self.root_case=c;self.parent_calls=[];self.other_calls=[];self.context=None
 def record_call(self,t):
  if t==p.PARENT:
   a=tuple(map(g.u32,self.arguments(4)));assert a[1]in GROUPS and a[3]in(0,1);assert a[2]==g.u32(g.s16(0 if a[1]in(3,5)else self.root_case.view)),('Bad connected view',a)
   self.parent_calls.append(a);self.context=a;self.case=replace(self.case,view=g.s16(a[2]),row=a[3],start=GROUPS[a[1]][0],stop=GROUPS[a[1]][1]);return
  if t in ROOTS:
   self.other_calls.append((t,tuple(map(g.u32,self.arguments(1 if t==ROOTS[3]else 2)))));return
  if t==p.RANGE:
   a=tuple(map(g.u32,self.arguments(3)));assert self.context and a[0]==self.context[1],('Range selector mismatch',a,self.context)
   assert a[1]!=a[2]and not((a[1]|a[2])&3);self.range_calls+=1;self.parent_events.append((t,a));return
  if t in(g.ENTRY,n.ALT):
   a=tuple(map(g.u32,self.arguments(3)));assert a[1]in self.allowed and a[2]==self.context[2],('Bad draw args',a,self.context);self.active=a[1];self.draw_id=int(t==n.ALT);self.called_targets.append(a);self.log.append((t,*a,n.fnv(n.boundary_values(self.memory))));return
  if t in(p.BEFORE,p.AFTER):
   a=tuple(map(g.u32,self.arguments(4 if t==p.BEFORE else 3)));assert a[1]in COLS and a[-1]==self.context[2]
   if t==p.BEFORE:assert a[2]==self.context[3],('Wrong stage row',a,self.context)
   self.parent_events.append((t,a));self.log.append((t,*a,n.fnv(n.boundary_values(self.memory))));return
  assert t in COUNTS,('Unknown caller helper',hex(t));a=tuple(map(g.u32,self.arguments(COUNTS[t])));self.other_calls.append((t,a))
 def hook(self,t):
  if t in(g.ENTRY,n.ALT,p.BEFORE,p.AFTER):return super().hook(t)
  assert t in COUNTS;t0,a=self.other_calls[-1];assert t0==t
  if t==0x1517D7B0:
   cursor=g.get(self.memory,a[0]);g.put(self.memory,cursor,0xBD000000|a[1]);g.put(self.memory,cursor+4,0);g.put(self.memory,a[0],cursor+8);value=0xDEADBEEF
  elif t==0x1517EFAC:value=int(self.root_case.gate==3)
  elif t in(0x1510B958,0x151D61B0):value=0xDEADBEEF
  else:
   cursor=a[0];assert g.OUTPUT<=cursor<g.OUTPUT+0x2000 and cursor&7==0,(hex(t),a)
   g.put(self.memory,cursor,0xBC000000|(t&65535));g.put(self.memory,cursor+4,sum(a[1:]));value=cursor+8
  for i in range(4):g.put(self.memory,self.r[29]+i*4,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=g.u32(value)
def state(m):return(g.public(m.memory),m.r[2],m.log,m.parent_calls,m.other_calls,m.called_targets,m.parent_events)
def main():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();callers={entry:function_words('func_%08X'%entry,elf)for entry in ROOTS};range_words=function_words('func_15168F84',elf)
 rom=(r/'conker/conker.us.bin').read_bytes()
 for name,item in packet.MANIFEST['caller_inventory'].items():
  address=int(item['VA'],16);length=item['retail_bytes'];at=g.elf_slot_offset(elf,address,length);start=int(item['ROM'],16)
  assert elf[at:at+length]==rom[start:start+length]
 original=list(struct.unpack('>348I',(r/'conker/conker.us.bin').read_bytes()[0x1949A8:0x194F18]));raw=g.bound_blob(*g.payload(o/'selected/candidate.o','func_151674F8'),g.SYMS)
 visits=set();count=draws=parents=0;rows=cases();ranges=set()
 for c in rows:
  memory,nodes,base=fixture(c);truth=Model(c,memory,nodes,base,original,callers,range_words).run();source=Model(c,memory,nodes,base,raw,callers,range_words).run();assert state(source)==state(truth),c
  assert truth.range_calls==len(truth.parent_calls)
  for args in truth.parent_calls:ranges.add(args[1])
  if c.root!=ROOTS[2]or c.gate==0:assert len(truth.parent_calls)==(8 if c.root==ROOTS[2]else 2),(c,truth.parent_calls)
  visits.update(truth.visits);count+=1;draws+=len(truth.called_targets);parents+=len(truth.parent_calls)
 actual_sites={int(v['VA'],16)for v in packet.MANIFEST['entry_audit']['direct_JALs']};assert actual_sites<=visits
 controls=[];c=Case(ROOTS[1],stages=True);memory,nodes,base=fixture(c);truth=Model(c,memory,nodes,base,original,callers,range_words).run()
 bad=raw[:];assert bad[17]>>26==0x2B;bad[17]&=~(31<<16)
 try:wrong=Model(c,memory,nodes,base,bad,callers,range_words).run()
 except AssertionError as e:assert'Wrong stage row'in str(e)
 else:assert state(wrong)!=state(truth)
 controls.append('lost-row-argument-home')
 bad=raw[:];assert bad[6]==0x00A08025;bad[6]=0x00008025
 try:Model(c,memory,nodes,base,bad,callers,range_words).run()
 except AssertionError as e:assert'Range selector mismatch'in str(e)
 else:raise AssertionError('Lost selector control survived')
 controls.append('lost-range-selector')
 report=dict(cases_per_parent_stream=count,complete_caller_functions=6,complete_caller_words=sum(map(len,callers.values())),all_14_actual_JAL_sites_executed=True,complete_actual_range_helper_words=len(range_words),range_helper_unexecuted=[i for i in range(len(range_words))if p.RANGE+i*4 not in visits],selectors=sorted(ranges),parent_invocations_per_stream=parents,draw_invocations_per_stream=draws,effective_controls=controls,source_installed=packet.installed(),matching_credit=0,limits='All six complete original/current callers and complete actual range helper, with complete raw/retail parent. Other rendering/output/pre/post/draw routines are bounded contracts; no hardware/gameplay claim.')
 (o/'callers.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
