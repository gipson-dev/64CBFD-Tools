"""Original installer, activation and complete127-word callback dispatcher on bounded pools."""
from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_phase_height_update_1511f788_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_phase_height_update_1511f788_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
PARENT=0x15113E54;RETURNS=(0x15113EF0,0x15113FC8);TABLE=0x80088C90;BASE=0x800DBEF4;TOTAL=0x800DBEF0;SKIP=0x800DBF98;GROUPCOUNT=0x80087380;GROUPBASE=0x800D23C0;GROUPS=0x350000;SCRIPT=0x360000;ACTIVATE=0x1511F768
def original():
 rom=(g.r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();text=(o/'baseline/conker/asm/13D350.s').read_text().split('glabel func_15113E54\n',1)[1].split('endlabel func_15113E54',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',text);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert len(blob)==508 and blob==rom[0x141304:0x141500]
 at=elf_slot_offset(elf,PARENT,508);assert elf[at:at+12]==bytes.fromhex('0000102503e0000800000000');assert[v[2]for _,n,v,_ in symbol_rows(elf)if n=='func_15113E54']==[12]
 table=rom[0x22D750:0x22DB80];assert len(table)==1072 and struct.unpack_from('>3I',table,65*12)==(g.ENTRY,ACTIVATE,0);at=elf_slot_offset(elf,TABLE,len(table));assert elf[at:at+len(table)]==table
 active=rom[0x14CC18:0x14CC38];assert len(active)==32;at=elf_slot_offset(elf,ACTIVATE,32);assert elf[at:at+32]==active
 for entry,off,n in((g.RNG,0xDAED0,72),(g.COS,0x750B0,352)):
  at=elf_slot_offset(elf,entry,n);assert elf[at:at+n]==rom[off:off+n]
 return list(struct.unpack('>127I',blob)),table,list(struct.unpack('>8I',active))
def activation(code,c):
 m=g.Machine(code,c);m.entry=ACTIVATE;m.code=g.Code(dict(zip(range(ACTIVATE,ACTIVATE+32,4),code)),m);m.r[5]=0x87654321;m.before=m.r[:];m.run();expected=g.fixture(c)
 if not g.read(expected,c.object+0x80):g.put(expected,c.object+0x80,1)
 assert g.public(m.memory,c)==g.public(expected,c)and not m.calls;return m
def installer(table):
 rom=(g.r/'conker/conker.us.bin').read_bytes();entry=0x1509EBBC;words=list(struct.unpack_from('>22I',rom,0xCC06C));c=g.Case();m=g.Machine(words,c);m.entry=entry;m.code=WindowCode(dict(zip(range(entry,entry+88,4),words)),m);m.code.ends=(0x1509ED5C,);m.memory.update({TABLE+i:v for i,v in enumerate(table)});m.memory.update({SCRIPT+i:165 for i in range(32)});g.put(m.memory,SCRIPT+8,65);m.r[16]=SCRIPT;m.r[2]=c.object;m.before=m.r[:];expected=dict(m.memory);g.put(expected,c.object+0x38,g.ENTRY);g.put(expected,c.object+0x78,ACTIVATE);expected[c.object+0x92]=0
 try:m.run();raise AssertionError('installer boundary missing')
 except WindowBoundary:pass
 assert g.public(m.memory,c)==g.public(expected,c)and m.r[2]==c.object;assert all(entry+4*i in m.visits for i in range(22));return m
def fixture(c,count,group,filter,active):
 m=g.fixture(c);g.put(m,BASE,g.ACTOR);g.put(m,TOTAL,count);g.put(m,SKIP,0);g.put(m,GROUPCOUNT,0 if group==0 else 1);g.put(m,GROUPBASE,GROUPS);m.update({GROUPS+i:(i*19+c.seed)&255 for i in range(48)});g.put(m,GROUPS+2,0 if group==1 else 2 if group==3 else 1,2);g.put(m,GROUPS+8,0x1000 if group==1 else 0x2000,2);g.put(m,GROUPS+10,0x2001,2)
 for p in(g.ACTOR,g.ACTOR+0xA0):
  g.put(m,p+0x38,g.ENTRY);g.put(m,p+0x78,ACTIVATE);m[p+0x92]=0;g.put(m,p+0x80,c.mode)
  if active and not c.mode:g.put(m,p+0x80,1)
 if filter==1:m[g.ACTOR+0x6F]=0
 elif filter==2:m[g.ACTOR+0x6E]=1
 elif filter==3:m[g.ACTOR+0xA0+0x6F]=0
 return m
def reference(initial,c):
 m=dict(initial);calls=[];packets=[];ops=[];csr=c.rm|c.flags;children=[]
 def child(p):
  nonlocal m,csr
  cc=replace(c,object=p,phase=c.phase-64);children.append((g.ENTRY,(p,)));m,more,pack,arith,csr=g.reference(m,cc,csr);calls.extend(more);packets.extend(pack);ops.extend(arith)
 count=g.signed(g.u32(g.read(m,TOTAL)-g.read(m,SKIP)))
 for i in range(max(0,count)):
  p=g.read(m,BASE)+0xA0*i
  if m[p+0x6F]&0x40 and not m[p+0x6E]:child(p)
 saved=(0,0,0,0)
 for i in range(max(0,g.signed(g.read(m,GROUPCOUNT)))):
  table=g.read(m,GROUPBASE);head=table+24*i
  if g.read(m,head+8,2)>>12!=2:continue
  n=g.read(m,head+2,2)
  for j in range(n):
   word=g.read(m,table+24*i+8+2*j,2)
   if word>>12!=2:continue
   p=g.read(m,BASE)+0xA0*(word&4095)
   if m[p+0x6F]&0x40 and not m[p+0x6E]:
    if j:
     for off,value,size in zip((0x5A,0x5C,0x5E,0x80),saved,(2,2,2,4)):g.put(m,p+off,value,size)
    child(p)
   if not j:saved=(g.half(g.read(m,p+0x5A,2)),g.half(g.read(m,p+0x5C,2)),g.half(g.read(m,p+0x5E,2)),g.read(m,p+0x80))
 return m,calls,packets,ops,csr,children
class Code(g.Code):
 def __getitem__(self,pc):
  m=self.owner
  if pc in RETURNS and m.pending:
   m.pending=False;m.children+=1;m.c=m.outer
   if m.poison is not None:m.r[2]=m.poison
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,parent,leaf,c,count,group,filter,active,raw=False,poison=None):
  super().__init__(parent,c,raw);self.entry=PARENT;self.code=Code({**dict(zip(range(PARENT,PARENT+508,4),parent)),**dict(zip(range(g.ENTRY,g.ENTRY+420,4),leaf))},self);self.memory=fixture(c,count,group,filter,active);self.initial=dict(self.memory);self.outer=c;self.parent_calls=[];self.children=0;self.pending=False;self.poison=poison;self.r[4]=0x87654321;self.before=self.r[:]
 def execute(self,w):
  if g.ENTRY<=self.current_pc<g.ENTRY+420:return super().execute(w)
  return g.FactoryOracle.execute(self,w)
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(self.arguments(1));self.parent_calls.append((t,args));self.c=replace(self.outer,object=args[0],phase=self.outer.phase-64);self.pending=True;return
  return super().record_call(t)
 def verify(self):
  memory,calls,packets,ops,csr,children=reference(self.initial,self.outer);assert(g.public(self.memory,self.outer),self.calls,self.packets,self.ops,self.fcsr,self.parent_calls)==(g.public(memory,self.outer),calls,packets,ops,csr,children),'complete dispatcher reference'
  assert self.children==len(children)and not self.pending;assert self.r[2]==g.read(memory,GROUPCOUNT);assert all(self.r[i]==self.before[i]for i in(*range(16,24),28,29,30,31))and self.f[20:]==self.before_f[20:];return self
def main():
 parent,table,active_code=original();installer(table)
 for mode in(0,1,2,0xFFFFFFFF):activation(active_code,g.Case(mode=mode))
 streams=[g.bound_blob(*g.payload(o/f,'func_1511F788'),g.symbols())for f in('original-target.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o','selected-owner.o')];seen=set();count=children=0
 for linear,group,gate,mode,activated in itertools.product((0,1,2),range(4),(0,1),(0,1,2),(0,1)):
  c=g.Case(gate=gate,mode=mode,mutation=count%4,rm=count&3,phase=8*(count&1),seed=count);models=[Connected(parent,w,c,linear,group,(count//3)%4,activated,i==4).run().verify()for i,w in enumerate(streams)];assert all(g.state(m)==g.state(models[0])for m in models[1:4]);g.raw_relation(models[0],models[4]);seen.update(p for p in models[0].visits if PARENT<=p<PARENT+508);count+=1;children+=models[0].children
 assert len(seen)==127,(len(seen),[hex(p)for p in set(range(PARENT,PARENT+508,4))-seen])
 for poison in(0,0xFFFFFFFF,0x80000000,0x13579BDF):Connected(parent,streams[0],g.Case(),2,3,0,False,poison=poison).run().verify()
 q=dict(parent_words_pinned=127,parent_words_executed=127,parent_frame=64,cases_per_stream=count,streams=5,connected_children_per_stream=children,installer_words=22,installer_all_words_executed=True,table='D_80088C90',row=65,row_VA='0x80088F9C',row_ROM='0x22DA5C',row_words=[hex(g.ENTRY),hex(ACTIVATE),'0x0'],full_table_bytes_pinned=1072,activation_slot_words=8,activation_modes=4,both_original_JALR_routes_executed=True,linear_group_gates_state_copy_and_complete_epilogue=True,return_poisons=4,void_one_argument_callback_ABI_qualified=True,original_parent_current_production_is_retained_12_byte_stub=True,original_caller_only_no_parent_matching_credit=True,private_parent_reference_only_public_memory_and_ordered_observers=True,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
