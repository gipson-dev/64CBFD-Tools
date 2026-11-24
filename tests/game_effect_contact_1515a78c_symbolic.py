"""Independent finite-path instruction proof; no projection import or map."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_effect_contact_1515a78c_match as p
r,o=p.ROOT,p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_ground_burst_callback_150df334_symbolic import ptr,add,byte,pack
class NeedChoice(Exception):pass
class State:
 def __init__(self,data,refs,choices,side):
  self.words=tuple(w[0]for w in struct.iter_unpack('>I',data));self.refs=refs;self.choices=choices;self.side=side;self.pc=0;self.steps=[];self.events=[];self.epoch=0;self.mem={};self.exposed=set();self.calls=0;self.cc=None;self.point=-16 if side==0 else-20
  self.reg=[('initial-register',i)for i in range(32)];self.reg[0]=0;self.reg[4]=ptr('record');self.reg[5]=ptr('position');self.reg[29]=ptr('stack');self.reg[31]=('original-return',);self.initial=self.reg[:];self.fp=[('initial-float-register',i)for i in range(32)];self.initial_fp=self.fp[:]
  for reg in(1,2,3,*range(6,16),24,25):self.reg[reg]=('independent-dead-register',side,reg)
  for reg in range(20):self.fp[reg]=('independent-dead-float-register',side,reg)
 def canonical(self,p):
  if isinstance(p,tuple)and p[0]=='pointer'and p[1]=='stack'and self.point<=p[2]<self.point+12:return ptr('point',p[2]-self.point)
  return p
 def canon(self,v):
  if isinstance(v,tuple):return self.canonical(v)if v and v[0]=='pointer'else tuple(self.canon(x)for x in v)
  return v
 def read(self,p,n,record=True):
  assert isinstance(p,tuple)and p[0]=='pointer',('invalid address',p)
  if p[1]=='stack':return pack([self.mem.get(add(p,i),('uninitialized-private',self.side,p[2]+i))for i in range(n)])
  v=('read',self.epoch,p,n)
  if record:self.events.append(('read',p,n,v))
  return v
 def write(self,p,value,n):
  assert p[0]=='pointer'and p[1]=='stack','Target wrote public RAM'
  for i in range(n):self.mem[add(p,i)]=(value&255 if isinstance(value,int)else('low-byte',value))if n==1 else byte(value,i)
 def location(self,i,rs,imm):
  ref=self.refs.get(4*i)
  if ref:assert ref[0][0]=='R_MIPS_LO16'and self.reg[rs]==('symbol-high',ref[0][1])and imm==0;return ptr('global:'+ref[0][1])
  return add(self.reg[rs],imm)
 def ins(self,i):
  self.steps.append(i);w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   assert fn==37 and self.reg[rt]==0,(i,hex(w));self.reg[rd]=self.reg[rs]
  elif op==9:self.reg[rt]=add(self.reg[rs],imm)
  elif op==12:
   v=self.reg[rs];self.reg[rt]=v&(w&65535)if isinstance(v,int)else('and32',v,w&65535)
  elif op==15:
   ref=self.refs.get(4*i);assert ref and ref[0][0]=='R_MIPS_HI16'and imm==0;self.reg[rt]=('symbol-high',ref[0][1])
  elif op in(35,36):self.reg[rt]=self.read(self.location(i,rs,imm),4 if op==35 else 1)
  elif op in(43,40):self.write(self.location(i,rs,imm),self.reg[rt],4 if op==43 else 1)
  elif op==49:self.fp[rt]=self.read(self.location(i,rs,imm),4)
  elif op==57:self.write(self.location(i,rs,imm),self.fp[rt],4)
  elif op==17:
   if rs==4:self.fp[rd]=self.reg[rt]
   elif rs==0:self.reg[rt]=self.fp[rd]
   elif rs==16 and fn in(0,2):self.fp[sa]=('float-add'if fn==0 else'float-mul',self.fp[rd],self.fp[rt])
   elif rs==16 and fn in(50,60,62):self.cc=('float-equal',*sorted((self.fp[rd],self.fp[rt]),key=repr))if fn==50 else('float-less'if fn==60 else'float-less-equal',self.fp[rd],self.fp[rt])
   else:raise AssertionError(('FP instruction',i,hex(w)))
  else:raise AssertionError(('instruction',i,hex(w)))
  self.reg[0]=0
 def arguments(self,n):return tuple(self.reg[4+i]if i<4 else self.read(add(self.reg[29],4*i),4)for i in range(n))
 def call(self,name):
  arity={'func_1515A60C':2,'func_1514672C':1,'func_15046C00':4,'func_150ADA68':0,'func_151D8E20':0,'func_151DBCBC':7};args=self.arguments(arity[name]);self.calls+=1
  points=(args[0],)if name in('func_1514672C','func_15046C00')else(args[4],)if name=='func_151DBCBC'else()
  for p in points:assert p==ptr('stack',self.point);self.exposed.add((p,12))
  snapshots=tuple(sorted(((self.canonical(p),n,tuple(self.read(add(p,i),1,False)for i in range(n)))for p,n in self.exposed),key=repr));self.events.append(('call',name,self.canon(args),self.canon(snapshots)))
  self.epoch+=1
  for p,n in self.exposed:
   for i in range(n):self.mem[add(p,i)]=('provider-byte',self.calls,self.canonical(add(p,i)))
  for i in range(max(4,len(args))):self.write(add(self.reg[29],4*i),('independent-outgoing-home',self.side,self.calls,i),4)
  for reg in(1,2,3,*range(4,16),24,25):self.reg[reg]=('independent-call-register',self.side,self.calls,reg)
  for reg in range(20):self.fp[reg]=('independent-call-float',self.side,self.calls,reg)
  self.reg[2]=('provider-return',name,self.calls);self.fp[0]=('provider-float-return',name,self.calls)
 def run(self):
  while True:
   assert len(self.steps)<180;i=self.pc;w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31
   if w==0x03e00008:
    assert self.reg[31]==self.initial[31];self.steps.append(i);self.ins(i+1);assert self.reg[16:24]==self.initial[16:24]and self.reg[28:]==self.initial[28:]and self.fp[20:]==self.initial_fp[20:];return
   if op==3:
    ref=self.refs.get(4*i);assert ref and ref[0][0]=='R_MIPS_26';self.reg[31]=('return-link',i+2);self.steps.append(i);self.ins(i+1);self.call(ref[0][1]);self.pc=i+2;continue
   fpbranch=op==17 and rs==8
   if fpbranch or op in(4,5,20,21):
    if fpbranch:key=self.cc;flip=not(rt&1);likely=bool(rt&2)
    else:
     a,b=self.reg[rs],self.reg[rt];key=True if a==b else a==b if isinstance(a,int)and isinstance(b,int)else('equal32',*sorted((a,b),key=repr));flip=op in(5,21);likely=op in(20,21)
    if isinstance(key,bool):value=key
    elif key in self.choices:value=self.choices[key]
    else:raise NeedChoice(key)
    taken=not value if flip else value;self.steps.append(i)
    if taken or not likely:self.ins(i+1)
    self.pc=i+1+(((w&65535)^32768)-32768)if taken else i+2
   else:self.ins(i);self.pc=i+1
 def signature(self):
  buffers=tuple(sorted(((self.canonical(p),n,tuple(self.read(add(p,i),1,False)for i in range(n)))for p,n in self.exposed),key=repr))
  return tuple(self.events),self.epoch,self.reg[2],buffers,tuple(self.reg[i]for i in(*range(16,24),28,29,30,31)),tuple(self.fp[20:])
def proof(raw,retail,write=True):
 assert len(raw[0])==392 and len(retail[0])==404;pending=[{}];completed=[];keys=set()
 while pending:
  choices=pending.pop();needs=[];models=[]
  for side,program in enumerate((raw,retail)):
   m=State(*program,choices,side);models.append(m)
   try:m.run();needs.append(None)
   except NeedChoice as e:needs.append(e.args[0])
  if any(n is not None for n in needs):
   assert needs[0]==needs[1],('branch predicates',needs);key=needs[0];assert key not in choices;keys.add(key);pending.extend(choices|{key:v}for v in(False,True))
  else:
   a,b=[m.signature()for m in models]
   if a!=b:
    if write:(o/'symbolic-mismatch.txt').write_bytes((repr(a)+'\n\n'+repr(b)).encode())
    raise AssertionError(('Independent effect-placement relation differs',choices))
   completed.append(dict(calls=models[0].calls,result=models[0].reg[2]))
  assert len(completed)+len(pending)<256
 q=dict(paths=len(completed),branch_keys=len(keys),opaque_call_counts=sorted({m['calls']for m in completed}),ordered_public_reads_calls_and_return_equal=True,all_exposed_point_bytes_havoced_at_every_later_provider=True,exact_float_add_and_multiply_operands=True,float_equality_predicate_symmetric=True,independent_dead_and_provider_register_home_clobbers=True,saved_register_lifetimes_equal=True,projection_imported=False,source_installed=p.installed(),matching_credit=0,scope='Mapped ordinary RAM; record/position/public globals may alias. Compatible returning o32 providers may mutate all public RAM and the retained initialized12-byte point, covariant under private point address renaming. Nontrapping single arithmetic retains exact operands; FP compare equality is symmetric. No raw private/fault/FCSR/trap identity, adjacent private access, numeric private/code-address reflection, transitive helper or gameplay acceptance.')
 if write:(o/'symbolic.json').write_bytes((json.dumps(q,indent=2)+'\n').encode())
 return q
if __name__=='__main__':print(json.dumps(proof(payload(o/'selected-final/candidate.o','func_1515A78C'),payload(o/'original-target.o','func_1515A78C'))),flush=True)
