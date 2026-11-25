"""Scoped acyclic integer proof with independent predicates and uninterpreted division.

This is structural overapproximation, not an SMT solver. All predicate assignments
are explored. Ordinary field memory and one optional guest-only hold-read mutation
are modeled. Physical scratch GPR values and raw instruction fault prefixes differ.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,struct,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_height_interpolation_151155c0_guest as g
from tools.experiments import game_height_interpolation_151155c0_match as p
o=p.OUT;POINT=g.POINT;MASK=0xffffffff
u=lambda n:n&MASK
signed=lambda n:((n&MASK)^0x80000000)-0x80000000
def isint(x):return isinstance(x,int)
def width(x):
 if isint(x):return max(1,x.bit_length())
 if x[0]=='input':return x[2]
 if x[0]=='slice':return x[3]
 if x[0]=='and':return x[2].bit_length()
 if x[0]=='bytes':return 8*(len(x)-1)
 if x[0]=='bool':return 1
 return 32
def band(x,n):
 n=u(n)
 if isint(x):return x&n
 if not n:return 0
 if n==MASK or n==(1<<n.bit_length())-1 and width(x)<=n.bit_length():return x
 if x[0]=='and':return band(x[1],x[2]&n)
 if x[0]=='sx16'and n<=65535:return band(x[1],n)
 if x[0]=='sar'and n in(255,65535):return ('slice',x[1],x[2],n.bit_length())
 return ('and',x,n)
def sx16(x):
 x=band(x,65535)
 return u(((x^32768)-32768))if isint(x)else('sx16',x)
def shift(x,n,right=False):
 if not n:return x
 if isint(x):return u(signed(x)>>n)if right else u(x<<n)
 if right and x[0]=='shl'and x[2]==n==16:return sx16(x[1])
 return ('sar'if right else'shl',x,n)
def add(a,b):
 if isint(a)and isint(b):return u(a+b)
 values=[];constant=0
 for x in(a,b):
  for y in x[1:]if isinstance(x,tuple)and x[0]=='add'else(x,):
   if isint(y):constant=u(constant+y)
   else:values.append(y)
 if constant:values.append(constant)
 return 0 if not values else values[0]if len(values)==1 else('add',*sorted(values,key=repr))
def neg(x):return u(-x)if isint(x)else x[1]if x[0]=='neg'else('neg',x)
def subtract(a,b):return 0 if a==b else add(a,neg(b))
def byte(x,i):
 if isint(x):return(x>>(8*i))&255
 if x[0]=='sx16'and i<2:return byte(x[1],i)
 if x[0]=='and'and x[2]&((1<<(8*i+8))-1)==(1<<(8*i+8))-1:return byte(x[1],i)
 return ('byte',x,i)
def join(values):
 if all(isint(v)for v in values):return int.from_bytes(bytes(values),'big')
 n=len(values)
 if all(isinstance(v,tuple)and v[0]=='byte'and v[1]==values[0][1]and v[2]==n-1-i for i,v in enumerate(values)):return band(values[0][1],(1<<(8*n))-1)
 return ('bytes',*values)
def inv(x):return not x if isinstance(x,bool)else x[1]if x[0]=='not'else('not',x)
def eq(a,b):
 if a==b:return True
 if isint(a)and isint(b):return a==b
 if isint(a)and not isint(b):return eq(b,a)
 if isint(b)and not isint(a):
  if b>((1<<width(a))-1):return False
  if a[0]=='bool'and b in(0,1):return a[1]if b else inv(a[1])
 return ('eq',*sorted((a,b),key=repr))
def lt(a,b):
 if a==b:return False
 return signed(a)<signed(b)if isint(a)and isint(b)else('slt',a,b)
class Fork(Exception):pass
class Trap(Exception):pass
class Machine:
 def __init__(self,words,choices=None,mutate=False,memory=None,registers=None):
  self.words=words;self.choices={}if choices is None else choices;self.mutate=mutate;self.r=[('input','gpr'+str(i),32)for i in range(32)]if registers is None else registers[:];self.r[0]=0
  if registers is None:self.r[4]=POINT;self.r[29]=g.STACK
  self.before=self.r[:];self.lo=self.hi=0;self.epoch=0;self.hold_reads=0;self.reads=[];self.writes=[];self.external=[];self.decisions=[];self.visits=[];self.trap=None
  self.memory={POINT+i:('input','retained'+str(i),8)for i in range(160)}if memory is None else dict(memory)
  if memory is None:
   for at,n,name in[(0x12,2,'height'),(0x3c,4,'packed'),(0x4f,1,'flags'),(0x5c,2,'delta'),(0x7c,4,'origin'),(0x80,4,'hold')]:self.store(POINT+at,n,('input',name,8*n),False)
 def store(self,a,n,v,record=True):
  assert isint(a)and POINT<=a and a+n<=POINT+160,(a,n)
  v=band(v,(1<<(8*n))-1)
  if record:self.writes.append((self.epoch,a-POINT,n,v));self.epoch+=1
  for i in range(n):self.memory[a+i]=byte(v,n-1-i)
 def load(self,a,n):
  assert isint(a)and POINT<=a and a+n<=POINT+160,(a,n)
  if a==POINT+0x80 and n==4:
   self.hold_reads+=1
   if self.mutate and self.hold_reads==2:
    v=('input','hold_after_height_commit',32);self.store(a,4,v,False);self.external.append((self.epoch,a-POINT,n,v));self.epoch+=1
  v=join([self.memory[a+i]for i in range(n)]);self.reads.append((self.epoch,a-POINT,n,v));return v
 def decision(self,p):
  if isinstance(p,bool):return p
  flip=p[0]=='not';key=p[1]if flip else p
  if key not in self.choices:raise Fork(key)
  value=self.choices[key];self.decisions.append((key,value));return not value if flip else value
 def execute(self,i):
  w=self.words[i];self.visits.append(i);op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768;a,b=self.r[rs],self.r[rt]
  if op==0:
   if fn==0:self.r[rd]=shift(b,sa)
   elif fn==3:self.r[rd]=shift(b,sa,True)
   elif fn==33:self.r[rd]=add(a,b)
   elif fn==35:self.r[rd]=subtract(a,b)
   elif fn==37:
    assert a==0 or b==0 or isint(a)and isint(b);self.r[rd]=b if a==0 else a if b==0 else a|b
   elif fn==42:
    p=lt(a,b);self.r[rd]=int(p)if isinstance(p,bool)else('bool',p)
   elif fn in(26,27):
    if isint(a)and isint(b):
     left,right=(signed(a),signed(b))if fn==26 else(a,b)
     if not right:self.lo=MASK if left>=0 else 1;self.hi=a
     else:q=(abs(left)//abs(right))*(-1 if(left<0)!=(right<0)else 1);self.lo=u(q);self.hi=u(left-q*right)
    else:self.lo=('sdiv'if fn==26 else'udiv',a,b);self.hi=('srem'if fn==26 else'urem',a,b)
   elif fn==18:self.r[rd]=self.lo
   elif fn==16:self.r[rd]=self.hi
   elif fn==13:assert(w>>6)&1023==0;raise Trap((w>>16)&1023)
   else:raise AssertionError(('special',i,hex(w)))
  elif op==9:self.r[rt]=add(a,u(imm))
  elif op==12:self.r[rt]=band(a,w&65535)
  elif op==15:self.r[rt]=(w&65535)<<16
  elif op in(33,35,36):
   v=self.load(add(a,u(imm)),{33:2,35:4,36:1}[op]);self.r[rt]=sx16(v)if op==33 else v
  elif op in(41,43):self.store(add(a,u(imm)),2 if op==41 else 4,b)
  else:raise AssertionError(('op',i,hex(w)))
  self.r[0]=0
 def run(self):
  pc=0
  try:
   for _ in range(500):
    assert 0<=pc<len(self.words),('outside',pc)
    w=self.words[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63;off=((w&65535)^32768)-32768
    if op in(4,5,20,21,6,7,22,23,1):
     if op in(4,5,20,21):p=eq(self.r[rs],self.r[rt]);p=inv(p)if op in(5,21)else p
     elif op in(6,22):p=inv(lt(0,self.r[rs]))
     elif op in(7,23):p=lt(0,self.r[rs])
     else:assert rt in(0,1);p=lt(self.r[rs],0);p=inv(p)if rt==1 else p
     taken=self.decision(p);self.visits.append(pc)
     if taken or op not in(20,21,22,23):self.execute(pc+1)
     pc=pc+1+off if taken else pc+2
    elif op==0 and fn==8:
     assert self.r[rs]==self.before[31];self.visits.append(pc);self.execute(pc+1);return self
    else:self.execute(pc);pc+=1
   raise AssertionError('Unbounded')
  except Trap as error:self.trap=error.args[0];return self
def observable(m):
 saved=tuple(m.r[i]for i in(0,4,*range(16,24),26,27,28,29,30,31));return m.trap,m.memory,m.writes,Counter(m.reads),m.external,m.decisions,saved,m.lo,m.hi,None if m.trap else m.r[2]
def prove(raw,retail,mutate=False):
 pending=[{}];paths=0;seen_a=set();seen_b=set()
 while pending:
  choices=pending.pop();assert len(choices)<=32 and len(pending)<20000
  try:a,b=Machine(raw,choices,mutate).run(),Machine(retail,choices,mutate).run()
  except Fork as error:
   key=error.args[0];assert key not in choices
   pending.extend([{**choices,key:False},{**choices,key:True}]);continue
  assert observable(a)==observable(b),('symbolic mismatch',mutate,choices,tuple(i for i,(x,y)in enumerate(zip(observable(a),observable(b)))if x!=y))
  paths+=1;seen_a.update(a.visits);seen_b.update(b.visits)
 return dict(paths=paths,raw_words_visited=len(seen_a),retail_words_visited=len(seen_b),retail_unvisited=sorted(set(range(103))-seen_b))
def main():
 blobs=[payload(o/f,'func_151155C0')[0]for f in['selected-final/owner-candidate.o','original-target.o']];raw,retail=[list(struct.unpack('>103I',v))for v in blobs];checks=0
 for c in g.cases():
  for ws in(raw,retail):
   actual=g.check(ws,c);model=Machine(ws,memory=g.fixture(c),registers=actual.before).run();assert model.memory==actual.memory and model.r==actual.r and(model.lo,model.hi)==(actual.lo,actual.hi)and model.trap==(7 if c.divisor==0 else None),(c,'concrete VM');checks+=1
 print(json.dumps(dict(independent_concrete_VM_checks=checks)),flush=True)
 ordinary=prove(raw,retail);print(json.dumps(dict(ordinary=ordinary)),flush=True);perturbed=prove(raw,retail,True);print(json.dumps(dict(guest_hold_read_perturbation=perturbed)),flush=True)
 controls=[]
 for name,find,change in [('delta-offset',lambda w:w>>26==41 and w&65535==0x5c,lambda w:w+2),('unsigned-division',lambda w:w>>26==0 and w&63==26,lambda w:w+1)]:
  bad=list(raw);at=next(i for i,w in enumerate(bad)if find(w));bad[at]=change(bad[at]);c=g.Case(current=-100,origin=50,target=-300,divisor=5,flags=4);concrete=Machine(bad,memory=g.fixture(c),registers=g.Machine(retail,c).before).run();assert concrete.trap is None
  try:prove(bad,retail)
  except AssertionError as error:assert'symbolic mismatch'in str(error);controls.append(dict(name=name,supported_complete_execution=True,rejected=True))
  else:raise AssertionError('Ineffective control')
 q=dict(raw_SHA256=hashlib.sha256(blobs[0]).hexdigest(),words=103,frame=0,independent_concrete_VM_checks=checks,ordinary=ordinary,guest_hold_read_perturbation=perturbed,arbitrary_record_field_bits_and_initial_GPRs=True,all_predicate_assignments_explored=True,signed_division_and_remainder_identical_operand_uninterpreted_operators=True,not_an_SMT_solver_or_general_binary_proof=True,ordered_public_writes_and_reads_per_write_epoch_equal=True,full_record_and_untouched_bytes_equal=True,return_V0_and_full_callee_state_equal=True,HI_LO_equal_on_normal_and_trap_paths=True,raw_scratch_GPR_and_physical_fault_prefix_equality_not_claimed=True,perturbation_is_guest_only_not_portable_concurrency_claim=True,effective_controls=controls,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
