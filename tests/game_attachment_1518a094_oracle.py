"""Private guest comparison: retail vs candidate, typed helper models."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_attachment_1518a094_match as p
from tools.experiments import game_attachment_1518a094_match as norm
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
LOOK=0x15083E90;TRANS=0x150A7960;TABLE=0x8008D5A0;CB=0x18010000;OBJ=0x30000;RES=0x40000;ALT=0x50000;MATRIX=0x60000
@dataclass(frozen=True)
class Case:
 initial:int;found:int;active:int;same:int;subtype:int;cbret:int;enabled:int;matrix:int;mutation:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base,size in ((OBJ,0x220),(RES,0x220),(ALT,0x220),(MATRIX,0x400),(TABLE-512,1024)):
  m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(size)})
 for i in range(-128,128):put(m,TABLE+i*4,CB)
 put(m,OBJ+0x188,RES if c.initial else 0);put(m,OBJ+0x58,0x1234567f);m[OBJ+0x18d]=0x42;m[OBJ+0x18e]=c.subtype&255;m[OBJ+0x18c]=2
 for res in (RES,ALT):put(m,res,c.active);m[res+0x3b]=0x42 if c.same else 0x43;put(m,res+0x1d4,MATRIX if c.matrix else 0)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def transform(m,args):
 for i in range(3):put(m,args[4+i],(args[1+i]^0x5a5a5a5a^(i*0x01010101))&0xffffffff)
def reference(c,initial):
 m=dict(initial);calls=[];ctx=OBJ+0x170;res=read(m,OBJ+0x188)
 if not res:
  calls.append((LOOK,(m[ctx+0x1d],)));res=RES if c.found else 0;put(m,ctx+0x18,res)
  if not res:return m,calls,0
 if not read(m,res) or m[ctx+0x1d]!=m[res+0x3b]:return m,calls,0
 subtype=(m[ctx+0x1e]^128)-128
 if subtype!=-1:
  calls.append((CB,(OBJ,"stack-byte",subtype&0xffffffff)))
  if c.mutation&1:put(m,ctx+0x18,ALT);put(m,OBJ+0x58,0x87654321);put(m,ctx+0xc,0x41a00000)
  if not c.cbret:return m,calls,0
  if not c.enabled:return m,calls,1
  res=read(m,ctx+0x18)
 matrix=read(m,res+0x1d4)
 if matrix:
  matrix+=m[ctx+0x1c]*64
  for i in range(2):
   args=(matrix,read(m,ctx+i*12),read(m,ctx+i*12+4),read(m,ctx+i*12+8),OBJ+0x34+i*12,OBJ+0x38+i*12,OBJ+0x3c+i*12);calls.append((TRANS,args));transform(m,args)
   if i==0 and c.mutation&2:put(m,ctx+0xC,0x3f123456);put(m,OBJ+0x58,0x55555555)
  flags=read(m,OBJ+0x58)|2;put(m,OBJ+0x58,flags);put(m,OBJ+0x58,flags&~4)
 else:put(m,OBJ+0x58,read(m,OBJ+0x58)&~2)
 return m,calls,1
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,memory=None):
  self.c=c;self.trans_count=0;super().__init__(words,fixture(c) if memory is None else memory,c,entry=p.ENTRY,arguments=(OBJ,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={LOOK:1,CB:3,TRANS:7,0x1518A214:3,0x1518A2E8:3,0x1518A324:3,0x151C9B64:3};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1]
  if t==LOOK:value=RES if c.found else 0
  elif t==CB:
   self.put(a[1],c.enabled,1)
   if c.mutation&1:self.put(OBJ+0x188,ALT,4);self.put(OBJ+0x58,0x87654321,4);self.put(OBJ+0x17c,0x41a00000,4)
   value=c.cbret
  else:
   assert t==TRANS;transform(self.memory,a);value=0xabcdef00
   if self.trans_count==0 and c.mutation&2:self.put(OBJ+0x17c,0x3f123456,4);self.put(OBJ+0x58,0x55555555,4)
   self.trans_count+=1
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def normalize(calls):return [(t,(a[0],"stack-byte",a[2])if t==CB else a)for t,a in calls]
def main():
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};candidate=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});normal,nrefs=norm.normalize(raw,refs);normalized=p.bound_blob(normal,nrefs,{n:lookup[n]for es in nrefs.values()for _,n in es});retail=struct.unpack_from(">96I",(p.root/"conker/conker.us.bin").read_bytes(),p.ROM);cases=[]
 for i,values in enumerate(itertools.product((0,1),(0,1),(0,1),(0,1),(-2,-1,0,1),(0,1),(0,1),(0,1),(0,1,2,3))):cases.append(Case(*values,phase=(i&1)*8,seed=i%3))
 visits=[set(),set(),set()]
 for c in cases:
  machines=[]
  for index,ws in enumerate((retail,candidate,normalized)):
   m=Oracle(ws,c);m.run();expected,calls,value=reference(c,m.initial);assert public(m.memory)==public(expected),(c,"public memory");assert normalize(m.calls)==calls,(c,normalize(m.calls),calls);assert m.r[2]==value,(c,"return",m.r[2],value);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];visits[index].update(m.visits);machines.append(m)
  a,b,d=machines;assert (a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace),(c,"normalized complete state")
 report=dict(cases=len(cases),executions=3*len(cases),retail_words_visited=len([v for v in visits[0] if p.ENTRY<=v<p.ENTRY+384]),candidate_words_visited=len([v for v in visits[1] if p.ENTRY<=v<p.ENTRY+len(candidate)*4]),normalized_complete_state=True,candidate="z000",helper_models=["lookup","subtype callback","matrix transform"],callback_writes_enabled=True,source_installed=False,byte_exact=False,hardware_or_faults_not_qualified=True)
 (p.out/"z000-guest.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
if __name__=="__main__":main()
