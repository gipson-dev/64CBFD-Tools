"""Seven static ignored-result routes and complete original small caller."""
from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_oriented_quad_constructor_15165f80_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_oriented_quad_constructor_15165f80_guest as g
from tools.tests import game_actor_coordinate_effect_dispatch_oracle as parent
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENT=0x150D8A34;RETURN=0x150D8AFC;PRE1=0x150D88E0;PRE2=0x151875E0

def use_def(w):
 op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 if op==0:
  if fn==8:return{rs},set(),'return'
  if fn in(0,2,3):return{rt},{rd},None
  assert fn in(33,35,37),hex(w);return{rs,rt},{rd},None
 if op==3:return set(),{31},'call'
 if op in(4,5):return{rs,rt},set(),'branch'
 if op in(9,10,11,12,13,14,32,33,35,36,37):return{rs},{rt},None
 if op==15:return set(),{rt},None
 if op in(40,41,43):return{rs,rt},set(),None
 if op in(49,57):return{rs},set(),None
 if op==17:return({rt},set(),None)if rs in(4,6)else(set(),{rt},None)if rs in(0,2)else(set(),set(),None)
 raise AssertionError(('unsupported static ABI prefix',hex(w)))

def static_returns():
 rom=(target_packet.ROOT/'conker/conker.us.bin').read_bytes();out=[]
 for c in json.loads((o/'qualified-context.json').read_bytes())['plain_JAL_callers']:
  off=int(c['call_ROM'],16)+8;start=off;limit=0
  while True:
   w=struct.unpack_from('>I',rom,off)[0];reads,writes,control=use_def(w);assert 2 not in reads,(c,hex(off),hex(w),'return consumed')
   if 2 in writes:why='explicit V0 overwrite';break
   if control=='call':
    delay=struct.unpack_from('>I',rom,off+4)[0];assert 2 not in use_def(delay)[0];why='following ABI call discards prior caller-saved V0';break
   if control=='return':assert c['function']=='func_150D8A34';why='known recovered void parent return';break
   if control=='branch':
    assert w>>21&31==w>>16&31==0,(c,hex(w));delay=struct.unpack_from('>I',rom,off+4)[0];reads,writes,_=use_def(delay);assert 2 not in reads
    if 2 in writes:why='unconditional branch-delay V0 overwrite';break
    delta=((w&65535)^32768)-32768;off+=4+4*delta
   else:off+=4
   limit+=1;assert limit<100,(c,'no bounded death')
  out.append(dict(function=c['function'],call=c['call_VA'],checked_words=(off-start)//4+1,reason=why))
 return out

def original_parent():
 text=(o/'baseline/conker/asm/105760.s').read_text().split('glabel func_150D8A34\n',1)[1].split('endlabel func_150D8A34',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',text);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(blob)==216;rom=(target_packet.ROOT/'conker/conker.us.bin').read_bytes();assert blob==rom[0x105EE4:0x105FBC];elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,PARENT,216);assert elf[at:at+216]==blob;return list(struct.unpack('>54I',blob))

def initial(c,pc):
 m=g.fixture(c);m.update(parent.fixture(pc));return m
def reference(memory,c,pc):
 m=dict(memory);home=g.STACK+pc.phase;vector=home-12;calls=[];ops=[];csr=c.rm|c.flags;g.put(m,home+4,pc.selector);g.put(m,home+8,pc.unused)
 def operation(kind,a,b=0):
  nonlocal csr
  ops.append((kind,a,b,csr,g.observation(m)));v,flags=g.trunc(a)if kind==13 else g.arithmetic(a,b,kind,csr&3);csr=(csr&~0x3F000)|flags;return v
 if g.read(m,pc.owner+0x1D4):
  g.put(m,home,pc.owner);calls.append((PRE1,(vector,pc.owner,pc.selector&255)))
  for i,v in enumerate((pc.x,pc.y,pc.z)):g.put(m,vector+4*i,v)
  parent.effect(m,pc,0);csr=(csr&~0x3F000)|c.provider_flags;calls.append((PRE2,(g.read(m,vector),g.read(m,vector+4),g.read(m,vector+8),30,15,7,g.read(m,parent.SYMS['D_800A0B30']),g.read(m,parent.SYMS['D_800A0B34']))));parent.effect(m,pc,1);csr=(csr&~0x3F000)|c.provider_flags
  x=operation(13,g.read(m,vector));height=operation(0,g.read(m,g.read(m,home)+0x180),g.fp.bits(4.));z=operation(13,g.read(m,vector+8));y=operation(13,height);args=(0xFFFFFFFF,x,y,z,4,50,0,255,0);calls.append((g.ENTRY,args))
  for i in range(4,9):g.put(m,home-64+4*i,args[i])
  m,childcalls,packets,childops,csr=g.reference(m,replace(c,values=args,phase=c.phase-64),csr);return m,calls,childcalls,packets,ops+childops,csr
 return m,calls,[],[],ops,csr

class Code(g.Code):
 def __getitem__(self,pc):
  m=self.owner
  if pc==RETURN and m.pending:
   m.pending=False;m.child_returns+=1;m.c=m.outer
   if m.poison is not None:m.r[2]=m.poison
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parentwords,leaf,c,pc,raw=False,poison=None):
  connected={**g.origin_code(),**dict(zip(range(g.ENTRY,g.ENTRY+408,4),leaf))};super().__init__(parentwords,c,raw,memory=initial(c,pc),entry=PARENT,connected=connected,arguments=(pc.owner,pc.selector,pc.unused));self.code=Code(self.code,self);self.pc_case=pc;self.outer=c;self.parent_calls=[];self.pending=False;self.child_returns=0;self.poison=poison
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(9)));self.parent_calls.append((t,args));self.c=replace(self.outer,values=args,phase=self.outer.phase-64);self.pending=True;return
  if t in(PRE1,PRE2):
   args=tuple(map(g.u32,self.arguments(3)))if t==PRE1 else(self.f[12],self.f[14],self.r[6],self.r[7],*(g.read(self.memory,self.r[29]+4*i)for i in range(4,8)));self.parent_calls.append((t,args));return
  super().record_call(t)
 def hook(self,t):
  if t not in(PRE1,PRE2):return super().hook(t)
  c=self.pc_case
  if t==PRE1:
   for i,v in enumerate((c.x,c.y,c.z)):g.put(self.memory,g.STACK+c.phase-12+4*i,v)
  parent.effect(self.memory,c,0 if t==PRE1 else 1)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xA5000002;self.fcsr=(self.fcsr&~0x3F000)|self.c.provider_flags
 def verify(self):
  m,parents,calls,packets,ops,csr=reference(self.initial,self.outer,self.pc_case);got=(g.public(self.memory,self.outer),self.parent_calls,self.calls,self.packets,self.ops,self.fcsr);want=(g.public(m,self.outer),parents,calls,packets,ops,csr);assert got==want,dict(case=str(self.pc_case),parts=[a==b for a,b in zip(got,want)],diff=[(hex(k),got[0].get(k),want[0].get(k))for k in set(got[0])|set(want[0])if got[0].get(k)!=want[0].get(k)][:12],packets=[(i,a[0])for i,(a,b)in enumerate(zip(self.packets,packets))if a!=b]);assert not self.pending and self.child_returns==bool(self.pc_case.active);return self

def main():
 static=static_returns();p=original_parent();streams=[g.bound_blob(*g.payload(o/f,'func_15165F80'),g.symbols())for f in('original-target.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o','selected-owner.o')];seen=set();count=children=0
 for active,selector,mutation,rm in itertools.product((0,0x50000),(3,255,0x87654304),(0,1,8,16,32,127),range(4)):
  pc=parent.Case(active=active,selector=selector,unused=selector^0x87654321,mutation=mutation,phase=8*(rm&1));c=g.Case(connected=1,phase=pc.phase,seed=count,rm=rm);models=[Connected(p,w,c,pc,i==4).run().verify()for i,w in enumerate(streams)];assert all(g.state(m)==g.state(models[0])for m in models[1:4]);assert all(m.parent_calls==models[0].parent_calls for m in models[1:]);g.raw_relation(models[0],models[4]);seen.update(v for v in models[0].visits if PARENT<=v<PARENT+216);count+=1;children+=models[0].child_returns
 poisons=[]
 for value in(0,0xFFFFFFFF,0x13579BDF):
  m=Connected(p,streams[0],g.Case(connected=1),parent.Case(),poison=value).run().verify();assert m.r[2]==value;poisons.append(hex(value))
 q=dict(static_ignored_result_routes=static,parent_words=54,parent_slot_words=55,parent_frame=64,parent_words_executed=len(seen),complete_original_parent_and_origin_connected=True,parent_frozen_ELF_matches_original=True,cases_per_stream=count,streams=5,connected_children_per_stream=children,independent_complete_parent_reference_with_ordered_FP=True,child_result_poison_controls=poisons,void_nine_argument_ABI_qualified=True,other_six_callers_static_only=True,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
