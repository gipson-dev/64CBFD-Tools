import itertools,json,math,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_twin_view_vertices_match as p
out=p.out;root=p.root
from tools.tests import game_record_vertex_callback_1513e83c_oracle as base
from tools.tests import game_billboard_quad_1513ead8_oracle as billboard
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
base.c.ROOT=root
base.rom.cache_clear()
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
TARGETS=(('151AC810','generated_1D92F0',11),('151DAE28','game_2062D0',14));ACTOR,BUFFER,ALT,STACK,TABLE=base.ACTOR,base.BUFFER,base.ALT,base.STACK,base.TABLE
BACKEND,COPY,ALLOC=base.BACKEND,base.COPY,base.ALLOC;AXIS_Z,AXIS_X=billboard.AXIS_Z,billboard.AXIS_X
u32,rd,wr,half,bits,floating=base.u32,base.rd,base.wr,base.half,base.bits,base.floating
@dataclass(frozen=True)
class Case(base.Case):
 axis:int=0

def fixture(c,order='big'):
 rd=lambda m,a,n:base.rd(m,a,n,order);wr=lambda m,a,v,n:base.wr(m,a,v,n,order)
 m=base.fixture(c,order)
 for view in set((half(c.view),0,1,2,3)):
  for p,v in zip((AXIS_Z+view*4,AXIS_X+view*4),billboard.AXES[c.axis]):
   for i in range(4):m.setdefault(u32(p+i),0)
   wr(m,p,bits(v),4)
 return m

def reference(initial,c,order='big',home=None):
 rd=lambda m,a,n:base.rd(m,a,n,order);wr=lambda m,a,v,n:base.wr(m,a,v,n,order)
 m=dict(initial);home=STACK+c.phase if home is None else home;frame=home-0x50;cursor=frame+0x4c;first=frame+0x48;fresh=frame+0x37;calls=[];wr(m,home+4,c.view,4)
 calls.append((BACKEND,(ACTOR+0x100,u32(half(c.view)),64,cursor,fresh)))
 if c.connected&4:
  p=rd(m,base.slot(c),4);m[fresh]=0
  if not p:
   calls.append((ALLOC,(128,1,2,1)));p=BUFFER if c.success else 0;wr(m,base.slot(c),p,4)
   if p:m[fresh]=1
  answer=u32(p+(0 if c.page else 64)) if p else 0
 else:m[fresh]=c.fresh;answer=base.output(c) if c.success else 0
 wr(m,cursor,answer,4);wr(m,first,answer,4)
 if not answer:return dict(memory=m,observed=base.public(m,c),calls=calls,value=0)
 if m[fresh]:
  for i in range(2):
   dest=u32(rd(m,base.slot(c),4)+i*64);calls.append((COPY,(dest,ACTOR+0xC0,64)));base.copy_bytes(m,dest,ACTOR+0xC0,64,order);base.effect(m,c,COPY,i+1,home,order)
 view=half(rd(m,home+4,4));width=base.mul(floating(rd(m,ACTOR+0x2c,4)),floating(rd(m,ACTOR+0x4c,4)));height=base.mul(floating(rd(m,ACTOR+0x30,4)),floating(rd(m,ACTOR+0x50,4)))
 forward=base.mul(floating(rd(m,AXIS_Z+4*view,4)),width);side=base.mul(floating(rd(m,AXIS_X+4*view,4)),width)
 for i in range(4):wr(m,rd(m,cursor,4)+i*16+6,0,2)
 for offsets,op in (((0x30,0x00),('add',0x34,side)),((0x12,0x02),('raw',0x38,0)),((0x34,0x04),('sub',0x3c,forward)),((0x20,0x10),('sub',0x34,side)),((0x32,0x22),('add',0x38,height)),((0x24,0x14),('add',0x3c,forward))):
  kind,field,arg=op;v=floating(rd(m,ACTOR+field,4));v=base.add(v,arg) if kind=='add' else billboard.sub(v,arg) if kind=='sub' else v;value=base.trunc(v)
  for off in offsets:wr(m,rd(m,cursor,4)+off,value,2)
 return dict(memory=m,observed=base.public(m,c),calls=calls,value=rd(m,first,4))
class Oracle(base.Oracle):
 def __init__(self,words,c,entry,memory=None):
  self.home=STACK+c.phase;self.copies=self.transforms=0;self.reference_leaf=False
  mem=fixture(c) if memory is None else memory;code=base.helpers(c);FactoryOracle.__init__(self,words,mem,c,entry=entry,s=dict(func_151D5D60=BACKEND,memcpy=COPY,D_800DD1D8=AXIS_Z,D_800DD1E8=AXIS_X),connected=code,arguments=(ACTOR,u32(c.view)))
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.target=entry
 def record_call(self,t):
  if t==self.target:
   self.calls.append((t,tuple(map(u32,self.arguments(2)))));self.home=self.r[29];return
  super().record_call(t)
 def hook(self,t):
  c=self.case;a=self.calls[-1][1];value=0
  if t==BACKEND:self.put(a[3],base.output(c) if c.success else 0,4);self.put(a[4],c.fresh,1)
  elif t==COPY:base.copy_bytes(self.memory,*a);self.copies+=1;base.effect(self.memory,c,t,self.copies,self.home);value=a[0]
  elif t==ALLOC:value=BUFFER if c.success else 0
  else:return super().hook(t)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def cases():
 for view,fresh,success,axis,scale,mutation in itertools.product((0,1,3,0x12340002),(0,1),(0,1),range(4),range(3),(0,1)):
  yield Case(view=view,fresh=fresh,success=success,axis=axis,scale=scale,mutation=mutation,seed=axis)
 for c in (Case(view=0xffff),Case(view=0x8000,fresh=0),Case(width=bits(-0.0),height=bits(-1.5)),Case(width=bits(32767.75)),Case(width=0x7fc12345),Case(width=0x7f800000)):
  yield c
 for alias,fresh,page in itertools.product((1,2),(0,1),(0,1)):
  yield Case(view=1,axis=2,scale=1,alias=alias,fresh=fresh,page=page)
 for connected,fresh,success,page in itertools.product((1,4,5),(0,1),(0,1),(0,1)):
  yield Case(view=3,axis=2,scale=1,connected=connected,fresh=fresh,success=success,page=page)
def words(target):
 data,fs,rs=parse_object(out/('variant_'+target+'.o'));a,n=fs['func_'+target]['value'],fs['func_'+target]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};return bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes();reports=[]
 for entry,offset,n in ((COPY,0x22ec0,11),(BACKEND,0x203210,52)):
  assert elf[elf_slot_offset(elf,entry,n*4):elf_slot_offset(elf,entry,n*4)+n*4]==rom[offset:offset+n*4],hex(entry)
 for target,owner,index in TARGETS:
  entry=int(target,16);retail=struct.unpack_from('>119I',rom,entry-0x15000000+0x2d4b0);candidate=words(target);seen=set();connected_seen=set();count=0
  for c in cases():
   for ws in (retail,candidate):
    m=Oracle(ws,c,entry);expected=reference(m.initial,c);m.run();actual=(base.public(m.memory,c),m.calls,m.r[2]);want=(expected['observed'],expected['calls'],expected['value']);assert actual==want,(target,c,m.calls,want[1],[(hex(k),v,actual[0].get(k))for k,v in want[0].items() if actual[0].get(k)!=v][:8]);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
    if ws is retail:
     seen.update(m.visits)
     if c.connected:connected_seen.update(m.visits)
   count+=1
  visits=sum(entry+4*i in seen for i in range(119));reports.append(dict(target=target,cases=count,retail_words_visited=visits,copy_words_visited=sum(COPY+4*i in connected_seen for i in range(11)),backend_words_visited=sum(BACKEND+4*i in connected_seen for i in range(52))))
 report=dict(targets=reports,helpers='modeled and connected copy/backend',helpers_match_current_elf=True,source_installed=False);(out/'guest_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
