"""Independent finite-path integer/RAM proof; imports no projection or word map."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_actor_command_1506e46c_match as p
r,o=p.ROOT,p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
MASK=0xffffffff
class NeedChoice(Exception):pass
def affine(v):
 if isinstance(v,int):return{},v&MASK
 if v[0]=='affine32':return dict(v[1]),v[2]
 return{v:1},0
def pack(terms,const):
 terms={k:v&MASK for k,v in terms.items()if v&MASK};const&=MASK
 if not terms:return const
 if len(terms)==1 and const==0:
  key,value=next(iter(terms.items()))
  if value==1:return key
 return('affine32',tuple(sorted(terms.items(),key=repr)),const)
def add(a,b):
 terms,const=affine(a);other,extra=affine(b)
 for key,value in other.items():terms[key]=terms.get(key,0)+value
 return pack(terms,const+extra)
def shift(v,k):
 terms,const=affine(v);return pack({key:value*(1<<k)for key,value in terms.items()},const*(1<<k))
def right(v,k):return(v>>k)if isinstance(v,int)else('right32',v,k)
def band(a,b):
 if isinstance(a,int)and isinstance(b,int):return a&b
 if a==0 or b==0:return 0
 if a==MASK:return b
 if b==MASK:return a
 return('and32',*sorted((a,b),key=repr))
def bor(a,b):
 if isinstance(a,int)and isinstance(b,int):return a|b
 if a==0:return b
 if b==0 or a==b:return a
 return('or32',*sorted((a,b),key=repr))
def equal(a,b):
 if a==b:return True
 if isinstance(a,int)and isinstance(b,int):return False
 return('equal32',*sorted((a,b),key=repr))
def ult(a,b):return int(a<b)if isinstance(a,int)and isinstance(b,int)else('unsigned-less32',a,b)
def address(kind,offset=0):return add(('address',kind),offset)
def stack_offset(p):
 terms,const=affine(p)
 return((const^0x80000000)-0x80000000)if terms=={('address','stack'):1}else None
class State:
 def __init__(self,data,refs,choices,side):
  self.words=tuple(x[0]for x in struct.iter_unpack('>I',data));self.refs=refs;self.choices=choices;self.side=side;self.pc=0;self.steps=[];self.events=[];self.calls=0;self.memory=('initial-public-memory',);self.private={}
  self.r=[('original-register',i)for i in range(32)];self.r[0]=0;self.r[4]=('argument',0);self.r[5]=('argument',1);self.r[6]=('argument',2);self.r[29]=address('stack');self.r[31]=('original-return',);self.before=self.r[:]
  for reg in(1,2,3,*range(7,16),24,25):self.r[reg]=('independent-dead-register',side,reg)
 def read(self,p,n):
  offset=stack_offset(p)
  if offset is not None:
   values=[self.private.get(offset+i,('initial-private-byte',offset+i))for i in range(n)]
   if all(isinstance(v,int)for v in values):return int.from_bytes(bytes(values),'big')
   if all(isinstance(v,tuple)and v[0]=='private-byte'and v[2:]==(i,n)for i,v in enumerate(values))and all(v[1]==values[0][1]for v in values):return values[0][1]
   return('private-bytes',tuple(values))
  value=('public-read',self.memory,p,n);self.events.append(('read',p,n,value));return value
 def write(self,p,n,v):
  offset=stack_offset(p)
  if offset is not None:
   for i in range(n):self.private[offset+i]=(v>>(8*(n-1-i)))&255 if isinstance(v,int)else('private-byte',v,i,n)
  else:self.events.append(('write',p,n,v));self.memory=('store',self.memory,p,n,v)
 def location(self,i,rs,imm):
  binding=self.refs.get(4*i)
  if binding:
   assert len(binding)==1;kind,name=binding[0];assert kind=='R_MIPS_LO16'and imm==0;terms,const=affine(self.r[rs]);high=('symbol-high',name);assert terms.pop(high,None)==1;terms[('address','global:'+name)]=terms.get(('address','global:'+name),0)+1;return pack(terms,const)
  return add(self.r[rs],imm)
 def ins(self,i):
  self.steps.append(i);w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn==0:self.r[rd]=shift(self.r[rt],sa)
   elif fn==2:self.r[rd]=right(self.r[rt],sa)
   elif fn==33:self.r[rd]=add(self.r[rs],self.r[rt])
   elif fn==36:self.r[rd]=band(self.r[rs],self.r[rt])
   elif fn==37:self.r[rd]=bor(self.r[rs],self.r[rt])
   elif fn==43:self.r[rd]=ult(self.r[rs],self.r[rt])
   else:raise AssertionError(('Unsupported R instruction',i,hex(w)))
  elif op==9:self.r[rt]=add(self.r[rs],imm)
  elif op==11:self.r[rt]=ult(self.r[rs],imm&MASK)
  elif op==12:self.r[rt]=band(self.r[rs],w&65535)
  elif op==13:self.r[rt]=bor(self.r[rs],w&65535)
  elif op==15:
   binding=self.refs.get(4*i)
   if binding:assert len(binding)==1 and binding[0][0]=='R_MIPS_HI16'and imm==0;self.r[rt]=('symbol-high',binding[0][1])
   else:self.r[rt]=(w&65535)<<16
  elif op in(35,36):self.r[rt]=self.read(self.location(i,rs,imm),4 if op==35 else 1)
  elif op==43:self.write(self.location(i,rs,imm),4,self.r[rt])
  else:raise AssertionError(('Unsupported instruction',i,hex(w)))
  self.r[0]=0
 def call(self,name):
  arity={'func_100107F8':1,'func_10010894':1,'func_151F2CDC':0,'func_150ADA20':0,'func_1000F568':2};args=tuple(self.r[4+i]for i in range(arity[name]));self.calls+=1;self.events.append(('call',name,args,self.memory));self.memory=('arbitrary-provider-public-memory',self.calls)
  for i in range(4):self.write(add(self.r[29],4*i),4,('independent-provider-home',self.side,self.calls,i))
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('independent-provider-register',self.side,self.calls,reg)
  self.r[2]=('provider-return',name,self.calls)
 def choose(self,key):
  if isinstance(key,bool):return key
  if key not in self.choices:raise NeedChoice(key)
  return self.choices[key]
 def run(self):
  while True:
   assert len(self.steps)<160,'Unexpected decoder loop';i=self.pc;w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31
   if w==0x03e00008:
    self.steps.append(i);self.ins(i+1);assert self.r[31]==self.before[31]and self.r[16:24]==self.before[16:24]and self.r[28:]==self.before[28:],('ABI state differs',self.r[16:],self.before[16:]);return
   if op==3:
    binding=self.refs.get(4*i);assert binding and len(binding)==1 and binding[0][0]=='R_MIPS_26';self.r[31]=('linked-return',i+2);self.steps.append(i);self.ins(i+1);self.call(binding[0][1]);self.pc=i+2;continue
   if op in(1,4,5,20,21):
    if op==1:
     value=self.r[rs];key=(value&0x80000000)!=0 if isinstance(value,int)else('negative32',value);negative=self.choose(key);assert rt in(0,1,2,3);taken=negative if rt in(0,2)else not negative;likely=rt in(2,3)
    else:key=equal(self.r[rs],self.r[rt]);eq=self.choose(key);taken=eq if op in(4,20)else not eq;likely=op in(20,21)
    self.steps.append(i)
    if taken or not likely:self.ins(i+1)
    self.pc=i+1+(((w&65535)^32768)-32768)if taken else i+2
   else:self.ins(i);self.pc=i+1
 def signature(self):return tuple(self.events),self.memory,self.r[2],tuple(self.r[i]for i in(*range(16,24),28,29,30,31)),tuple(self.private.get(i)for i in range(8))
def proof(raw,truth,write=True):
 assert len(raw[0])==380 and len(truth[0])==400;pending=[{}];completed=[];keys=set()
 while pending:
  choices=pending.pop();needs=[];signatures=[];counts=[]
  for side,(data,refs)in enumerate((raw,truth)):
   m=State(data,refs,choices,side)
   try:m.run();needs.append(None);signatures.append(m.signature());counts.append(m.calls)
   except NeedChoice as e:needs.append(e.args[0]);signatures.append(None)
  if any(v is not None for v in needs):
   assert needs[0]==needs[1],('Independent branch predicates differ',needs,choices);key=needs[0];assert key not in choices;keys.add(key)
   for answer in(False,True):pending.append(choices|{key:answer})
  else:assert signatures[0]==signatures[1],('Independent command relation differs',choices,signatures);completed.append(dict(calls=counts[0],result=signatures[0][2]))
  assert len(pending)+len(completed)<4096,'Unexpected path explosion'
 q=dict(paths=len(completed),symbolic_branch_keys=len(keys),call_counts=sorted({v['calls']for v in completed}),ordered_public_reads_calls_writes_equal=True,all_public_memory_and_return_words_equal=True,independent_dead_registers_and_provider_home_clobbers=True,entry_argument_homes_and_o32_saved_roles_equal=True,projection_imported=False,source_installed=p.installed(),matching_credit=0,scope='All 32-bit input/command/provider-result words, ordinary mapped nontrapping RAM and compatible returning o32 providers. Public actor/command/table aliases are permitted. The private frame and incoming argument homes are not exposed; code/return-address reflection is excluded. Raw full private/fault identity and transitive provider implementation semantics are not claimed.')
 if write:(o/'symbolic.json').write_bytes((json.dumps(q,indent=2)+'\n').encode())
 return q
if __name__=='__main__':print(json.dumps(proof(payload(o/'selected-final/candidate.o','func_1506E46C'),payload(o/'original-target.o','func_1506E46C'))),flush=True)
