"""Independent finite-path public-memory/FP relation, without a projection map."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_actor_state_motion_150b12fc_match as p
r,o=p.ROOT,p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
MASK=0xffffffff
def addr(kind,offset=0):return('address',kind,offset)
def plus(a,b):
 if isinstance(a,int)and isinstance(b,int):return(a+b)&MASK
 if b==0:return a
 if a==0:return b
 if isinstance(a,tuple)and a[0]=='address'and isinstance(b,int):return addr(a[1],a[2]+b)
 return('add32',a,b)
def trunc(v,n):
 if n==4:return v
 if isinstance(v,int):return v&((1<<(8*n))-1)
 if v[0]=='sext'and v[1]==8*n:return trunc(v[2],n)
 if v[0]=='read'and v[-1]==n:return v
 return('low',8*n,v)
def sext(v,n):
 if isinstance(v,int):return((v&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))&MASK
 return('sext',n,v)
def integer(v):return(v^0x80000000)-0x80000000
def disjoint(a,n,b,m):
 if not(isinstance(a,tuple)and isinstance(b,tuple)and a[0]==b[0]=='address'):return False
 if a[1]!=b[1]:return True # Distinct owner/global storage objects.
 return a[2]+n<=b[2]or b[2]+m<=a[2]
def select(memory,a,n):
 if memory[0]=='store':
  _,old,b,m,value=memory
  if a==b and n==m:return value
  if disjoint(a,n,b,m):return select(old,a,n)
 return('read',memory,a,n)
class State:
 def __init__(self,data,refs,high,low,returned):
  self.words=struct.unpack('>98I',data);self.refs=refs;self.high=high;self.low=low;self.returned=returned;self.pc=0;self.steps=[];self.events=[];self.memory=('initial-public-memory',);self.private={};self.calls=0;self.compares=0
  self.reg=[('initial-register',i)for i in range(32)];self.reg[0]=0;self.reg[4]=addr('owner');self.reg[29]=addr('stack');self.reg[31]=('original-return',);self.initial=self.reg[:];self.fp=[('initial-float',i)for i in range(32)];self.initial_fp=self.fp[:];self.condition=None
 def read(self,a,n):
  if isinstance(a,tuple)and a[0]=='address'and a[1]=='stack':
   values=[self.private.get(plus(a,i),('uninitialized-private-byte',a[2]+i))for i in range(n)]
   if all(isinstance(v,int)for v in values):return int.from_bytes(bytes(values),'big')
   if all(isinstance(v,tuple)and v[0]=='private-byte'and v[2:]==(i,n)for i,v in enumerate(values))and all(v[1]==values[0][1]for v in values):return values[0][1]
   return('private-bytes',tuple(values))
  return select(self.memory,a,n)
 def write(self,a,n,v):
  v=trunc(v,n)
  if isinstance(a,tuple)and a[0]=='address'and a[1]=='stack':
   for i in range(n):self.private[plus(a,i)]=(v>>(8*(n-1-i)))&255 if isinstance(v,int)else('private-byte',v,i,n)
  else:self.memory=('store',self.memory,a,n,v)
 def location(self,i,rs,imm):
  binding=self.refs.get(4*i)
  if binding:
   assert len(binding)==1;kind,name=binding[0];assert kind=='R_MIPS_LO16'and self.reg[rs]==('symbol-high',name)and imm==0,(i,binding,self.reg[rs],imm);return addr('global:'+name)
  return plus(self.reg[rs],imm)
 def ins(self,i):
  self.steps.append(i);w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn==37:assert self.reg[rt]==0;self.reg[rd]=self.reg[rs]
   elif fn==33:self.reg[rd]=plus(self.reg[rs],self.reg[rt])
   elif fn==35:
    a,b=self.reg[rs],self.reg[rt];self.reg[rd]=(a-b)&MASK if isinstance(a,int)and isinstance(b,int)else('sub32',a,b)
   elif fn in(0,3):
    a=self.reg[rt];self.reg[rd]=((a<<sa)&MASK if fn==0 else(integer(a)>>sa)&MASK)if isinstance(a,int)else('shl32'if fn==0 else'sar32',a,sa)
   else:raise AssertionError(('R instruction',i,hex(w)))
  elif op==9:self.reg[rt]=plus(self.reg[rs],imm)
  elif op==15:
   binding=self.refs.get(4*i)
   if binding:assert len(binding)==1 and binding[0][0]=='R_MIPS_HI16'and imm==0;self.reg[rt]=('symbol-high',binding[0][1])
   else:self.reg[rt]=(w&65535)<<16
  elif op in(33,35,36,37):
   n={33:2,35:4,36:1,37:2}[op];v=self.read(self.location(i,rs,imm),n);self.reg[rt]=sext(v,16)if op==33 else v
  elif op in(40,41,43):self.write(self.location(i,rs,imm),{40:1,41:2,43:4}[op],self.reg[rt])
  elif op==49:self.fp[rt]=self.read(self.location(i,rs,imm),4)
  elif op==57:self.write(self.location(i,rs,imm),4,self.fp[rt])
  elif op==17:
   if rs==4:self.fp[rd]=self.reg[rt]
   elif rs==0:self.reg[rt]=self.fp[rd]
   elif rs==20 and fn==32:
    v=self.fp[rd];self.fp[sa]=int.from_bytes(struct.pack('>f',float(integer(v))),'big')if isinstance(v,int)else('int32-to-float32',v)
   elif rs==16 and fn in(0,1,2):self.fp[sa]=({0:'float-add',1:'float-sub',2:'float-mul'}[fn],self.fp[rd],self.fp[rt])
   elif rs==16 and fn==6:self.fp[sa]=self.fp[rd]
   elif rs==16 and fn==60:
    assert self.compares<2;choice=self.high if self.compares==0 else self.low;self.compares+=1;self.condition=choice;self.events.append(('ordered-float-lt',self.fp[rd],self.fp[rt],choice))
   else:raise AssertionError(('FP instruction',i,hex(w)))
  else:raise AssertionError(('Instruction',i,hex(w)))
  self.reg[0]=0
 def args(self,n):return tuple(self.reg[4+i]if i<4 else self.read(plus(self.reg[29],4*i),4)for i in range(n))
 def call(self,name):
  arity={'func_15058EA4':7,'func_15056B08':1,'func_15059140':1,'func_150535F4':1,'func_1502178C':3};a=self.args(arity[name]);self.calls+=1;self.events.append(('call',name,a,self.memory));self.memory=('arbitrary-public-after-call',self.calls)
  for i in range(max(4,len(a))):self.write(plus(self.reg[29],4*i),4,('clobbered-outgoing-home',self.calls,i))
  for reg in(1,2,3,*range(4,16),24,25):self.reg[reg]=('call-register',self.calls,reg)
  for reg in range(20):self.fp[reg]=('call-float',self.calls,reg)
  self.reg[2]=('predicate-return',)if name=='func_150535F4'and self.returned else 0 if name=='func_150535F4'else('call-register',self.calls,2)
 def run(self):
  while True:
   assert len(self.steps)<200;i=self.pc;w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31
   if w==0x03e00008:
    assert self.reg[31]==self.initial[31];self.steps.append(i);self.ins(i+1);assert self.reg[16:24]==self.initial[16:24]and self.reg[28:]==self.initial[28:]and self.fp[20:]==self.initial_fp[20:];return
   if op==3:
    binding=self.refs.get(4*i);assert binding and len(binding)==1 and binding[0][0]=='R_MIPS_26';self.reg[31]=('link-return',i+2);self.steps.append(i);self.ins(i+1);self.call(binding[0][1]);self.pc=i+2;continue
   likely=False;taken=None
   if op in(4,5):
    a,b=self.reg[rs],self.reg[rt]
    if a==b:equal=True
    elif isinstance(a,int)and isinstance(b,int):equal=a==b
    elif a==('predicate-return',)and b==0:equal=False
    else:raise AssertionError(('Unresolved integer branch',i,a,b))
    taken=equal if op==4 else not equal
   elif op==17 and rs==8:
    assert rt in(0,1,2,3)and self.condition is not None;likely=bool(rt&2);taken=self.condition==bool(rt&1)
   if taken is not None:
    self.steps.append(i)
    if taken or not likely:self.ins(i+1)
    self.pc=i+1+(((w&65535)^32768)-32768)if taken else i+2
   else:self.ins(i);self.pc=i+1
 def signature(self):return tuple(self.events),self.memory,tuple(self.reg[i]for i in(*range(16,24),28,29,30,31)),tuple(self.fp[20:])
def proof(raw,retail,write=True):
 assert len(raw[0])==len(retail[0])==392;paths=[]
 for high,low in((True,False),(False,True),(False,False)):
  for returned in(False,True):
   a=State(*raw,high,low,returned);b=State(*retail,high,low,returned);a.run();b.run()
   if a.signature()!=b.signature():
    if write:(o/'symbolic-mismatch.txt').write_bytes((repr(a.signature())+'\n\n'+repr(b.signature())).encode())
    raise AssertionError(('Independent state-motion relation differs',high,low,returned))
   paths.append(dict(high_clamp=high,low_clamp=low,predicate_nonzero=returned,calls=a.calls))
 q=dict(paths=paths,independent_public_memory_and_call_states_equal=True,ordered_FP_operands_and_conditions_equal=True,arbitrary_compatible_provider_public_effects=True,table_and_row_aliases_preserved_by_functional_memory=True,saved_integer_and_float_registers_restore=True,projection_imported=False,proof_installs_source=False,matching_credit=0,scope='Normal nontrapping ordinary RAM and compatible returning o32 providers without private-address or return-address reflection. Owner and named global storage objects are distinct; table and row pointers may alias public owner storage. Public reads may commute only across statically disjoint stores. Raw private/fault-state identity is not claimed.')
 if write:(o/'symbolic.json').write_bytes((json.dumps(q,indent=2)+'\n').encode())
 return q
if __name__=='__main__':print(json.dumps(proof(payload(o/'selected-final/candidate.o','func_150B12FC'),payload(o/'original-target.o','func_150B12FC'))),flush=True)
