"""Independent finite-path raw/retail interpreter; no projection import or map."""
from pathlib import Path
import copy,json,struct,sys
from tools.experiments import game_ground_burst_callback_150df334_match as p
r,o=p.ROOT,p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
MASK=0xffffffff
def ptr(kind,offset=0):return('pointer',kind,offset)
def add(a,b):
 if isinstance(a,int)and isinstance(b,int):return(a+b)&MASK
 if b==0:return a
 if isinstance(a,tuple)and a[0]=='pointer'and isinstance(b,int):return ptr(a[1],a[2]+b)
 return('add32',a,b)
def byte(v,i):return(v>>(8*(3-i)))&255 if isinstance(v,int)else('byte',v,i)
def pack(values):
 if all(isinstance(v,int)for v in values):return int.from_bytes(bytes(values),'big')
 if len(values)==4 and all(isinstance(v,tuple)and v[0]=='byte'and v[2]==i for i,v in enumerate(values))and all(v[1]==values[0][1]for v in values):return values[0][1]
 return('bytes'+str(len(values)),tuple(values))
def signed(v):return(v^0x80000000)-0x80000000

class State:
 def __init__(self,data,refs,raw,hit):
  self.words=list(struct.unpack('>'+str(len(data)//4)+'I',data));self.refs=refs;self.raw=raw;self.hit=hit;self.pc=0;self.steps=[];self.epoch=0;self.mem={};self.events=[];self.escaped=set();self.calls=0
  self.reg=[('initial-register',i)for i in range(32)];self.reg[0]=0;self.reg[4]=ptr('owner');self.reg[29]=ptr('stack');self.reg[31]=('original-return',);self.initial=self.reg[:];self.fp=[('initial-float-register',i)for i in range(32)];self.initial_fp=self.fp[:];self.hi=self.lo=('initial-hi-lo',)
  self.block=-76 if raw else-80
 def canonical(self,p):
  if isinstance(p,tuple)and p[0]=='pointer'and p[1]=='stack'and self.block<=p[2]<self.block+76:return ptr('owned-block',p[2]-self.block)
  return p
 def initial_byte(self,p):
  p=self.canonical(p)
  if p[1]=='owner':return('public-byte',self.epoch,p[2])
  assert p[1]in('owned-block','stack');return('private-initial-byte',p[1],p[2])
 def read(self,p,n,record=True):
  assert p[0]=='pointer';values=[self.mem.get(add(p,i),self.initial_byte(add(p,i)))for i in range(n)];value=pack(values)
  if record and p[1]=='owner':self.events.append(('read',p,n,value))
  return value
 def write(self,p,value,n):
  assert p[0]=='pointer'and p[1]=='stack','Routine wrote public memory'
  for i in range(n):self.mem[add(p,i)]=(value&255 if isinstance(value,int)else('low-byte',value))if n==1 else byte(value,i)
 def ins(self,i):
  self.steps.append(i);w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn==37:
    assert self.reg[rt]==0;self.reg[rd]=self.reg[rs]
   elif fn==0:
    x=self.reg[rt];self.reg[rd]=(x<<sa)&MASK if isinstance(x,int)else('shl32',x,sa)
   elif fn==3:
    x=self.reg[rt];self.reg[rd]=(signed(x)>>sa)&MASK if isinstance(x,int)else('sext16',x[1])if x[0]=='shl32'and x[2]==sa==16 else('sar32',x,sa)
   elif fn in(26,27):
    assert isinstance(self.reg[rt],int)and self.reg[rt]!=0
    self.hi=('srem'if fn==26 else'urem',self.reg[rs],self.reg[rt]);self.lo=('sdiv'if fn==26 else'udiv',self.reg[rs],self.reg[rt])
   elif fn==16:self.reg[rd]=self.hi
   else:raise AssertionError(('R operation',i,hex(w)))
  elif op==9:self.reg[rt]=add(self.reg[rs],imm)
  elif op==15:self.reg[rt]=(w&65535)<<16
  elif op in(35,36):self.reg[rt]=self.read(add(self.reg[rs],imm),4 if op==35 else 1)
  elif op in(43,40):self.write(add(self.reg[rs],imm),self.reg[rt],4 if op==43 else 1)
  elif op==49:self.fp[rt]=self.read(add(self.reg[rs],imm),4)
  elif op==57:self.write(add(self.reg[rs],imm),self.fp[rt],4)
  elif op==17:
   if rs==4:self.fp[rd]=self.reg[rt]
   elif rs==0:self.reg[rt]=self.fp[rd]
   elif rs==16 and fn in(0,1):self.fp[sa]=('float-add'if fn==0 else'float-sub',self.fp[rd],self.fp[rt])
   else:raise AssertionError(('FP operation',i,hex(w)))
  else:raise AssertionError(('operation',i,hex(w)))
  self.reg[0]=0
 def condition(self,w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31
  if op not in(4,5,20,21):return None
  a,b=self.reg[rs],self.reg[rt]
  if isinstance(a,int)and isinstance(b,int):equal=a==b
  elif a==b:equal=True
  elif b==0 and a==('ground-result',):equal=not self.hit
  else:raise AssertionError(('Unresolved branch',self.pc,a,b))
  return equal if op in(4,20)else not equal
 def arguments(self,n):return tuple(self.reg[4+i]if i<4 else self.read(add(self.reg[29],4*i),4)for i in range(n))
 def canon_value(self,v):
  if isinstance(v,tuple):
   if v and v[0]=='pointer':return self.canonical(v)
   return tuple(self.canon_value(x)for x in v)
  return v
 def call(self,name):
  arity={'func_1504697C':4,'func_150ADA20':0,'func_150E83AC':4,'func_151A9834':9};assert name in arity,name;n=arity[name];args=self.arguments(n);self.calls+=1
  buffers=((args[0],12),(args[3],36))if name=='func_1504697C'else((args[0],12),)if name=='func_150E83AC'else((args[0],12),(args[3],36))if name=='func_151A9834'else()
  for p,size in buffers:
   assert p[0]=='pointer'and p[1]in('owner','stack')
   if p[1]=='stack':assert self.block<=p[2]and p[2]+size<=self.block+76;self.escaped.add((p,size))
  snapshots=tuple(sorted(((self.canonical(p),size,tuple(self.read(add(p,i),1,False)for i in range(size)))for p,size in self.escaped),key=repr))
  supplied=tuple((self.canonical(p),size,tuple(self.read(add(p,i),1,False)for i in range(size)))for p,size in buffers)
  self.events.append(('call',name,self.canon_value(args),snapshots,supplied))
  # Coupled arbitrary public effects and arbitrary writes to every escaped
  # buffer, including pointers retained by any earlier compatible provider.
  self.epoch+=1
  for p,size in self.escaped:
   for i in range(size):self.mem[add(p,i)]=('provider-byte',self.calls,self.canonical(add(p,i)))
  for i in range(max(n,4)):self.write(add(self.reg[29],4*i),('outgoing-home-clobber',self.calls,i),4)
  for reg in(1,2,3,*range(4,16),24,25):self.reg[reg]=('call-register',self.calls,reg)
  for reg in range(20):self.fp[reg]=('call-float-register',self.calls,reg)
  self.hi,self.lo=('call-hi',self.calls),('call-lo',self.calls)
  if name=='func_1504697C':self.reg[2]=('ground-result',)if self.hit else 0
  elif name=='func_150ADA20':self.reg[2]=('random-u32',self.calls)
 def run(self):
  while True:
   assert len(self.steps)<220,'Unexpected loop or control flow';i=self.pc;w=self.words[i];op=w>>26
   if w==0x03e00008:
    assert self.reg[31]==self.initial[31];self.steps.append(i);self.ins(i+1)
    assert self.reg[16:24]==self.initial[16:24]and self.reg[28:]==self.initial[28:]and self.fp[20:]==self.initial_fp[20:],'Saved-register lifetime changed';return
   if op==3:
    refs=self.refs.get(4*i);assert refs and len(refs)==1 and refs[0][0]=='R_MIPS_26';self.reg[31]=('link-return',i+2);self.steps.append(i);self.ins(i+1);self.call(refs[0][1]);self.pc=i+2;continue
   taken=self.condition(w)
   if taken is not None:
    self.steps.append(i)
    if taken or op not in(20,21):self.ins(i+1)
    self.pc=i+1+(((w&65535)^32768)-32768)if taken else i+2
   else:self.ins(i);self.pc=i+1
 def signature(self):
  final=tuple(sorted(((self.canonical(p),n,tuple(self.read(add(p,i),1,False)for i in range(n)))for p,n in self.escaped),key=repr))
  return tuple(self.events),final,tuple(self.reg[i]for i in(*range(16,24),28,29,30,31)),tuple(self.fp[20:])

def proof(raw,retail,write=True):
 assert len(raw[0])==392 and len(retail[0])==388
 paths=[]
 for hit in(False,True):
  left=State(*raw,True,hit);right=State(*retail,False,hit);left.run();right.run()
  if left.signature()!=right.signature():
   if write:(o/'symbolic-mismatch.txt').write_bytes((repr(left.signature())+'\n\n'+repr(right.signature())).encode())
   raise AssertionError(('Independent ground-burst relation differs',hit))
  assert left.calls==right.calls==5;paths.append(dict(ground_return_nonzero=hit,opaque_calls=5,escaped_private_buffers=len(left.escaped)))
 q=dict(paths=paths,ordered_public_reads_and_calls_equal=True,escaped_buffer_bytes_and_initial_padding_related=True,all_previous_private_pointer_escapes_havoced_at_each_call=True,unsigned_remainders_and_argument_narrowing_equal=True,all_o32_saved_registers_restore=True,projection_imported=False,source_installed=False,matching_credit=0,scope='Normal nontrapping executions in mapped ordinary RAM, owner disjoint from the private frame; compatible returning o32 providers covariant under private-pointer renaming, with arbitrary public effects and writes to all previously escaped bounded buffers. Numeric private-address/return-address reflection and raw private/fault-state identity are not claimed.')
 if write:(o/'symbolic.json').write_bytes((json.dumps(q,indent=2)+'\n').encode())
 return q
if __name__=='__main__':
 raw=payload(o/'selected-final/candidate.o','func_150DF334');retail=payload(o/'original-target.o','func_150DF334');print(json.dumps(proof(raw,retail)),flush=True)
