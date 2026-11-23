"""Leaf-specific symbolic path/loop proof. Unknown instructions fail closed."""
from pathlib import Path
import copy,json,struct,sys
from tools.experiments import game_group_record_pairs_15022024_match as p
r=p.ROOT;o=p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_unmatched_pair_lookup_20261123_guest as g
def atom(s):return ('lin',0,((s,1),))
def num(n):return ('lin',n&0xffffffff,())
def plus(a,b):
 assert a[0]==b[0]=='lin',(a,b)
 terms=dict(a[2])
 for s,v in b[2]:terms[s]=(terms.get(s,0)+v)&0xffffffff
 return ('lin',(a[1]+b[1])&0xffffffff,tuple(sorted((s,v)for s,v in terms.items()if v)))
def scale(a,k):return ('lin',(a[1]*k)&0xffffffff,tuple((s,(v*k)&0xffffffff)for s,v in a[2]if(v*k)&0xffffffff))
Z=num(0)
def eq(a,b):
 if a==b:return True
 if a[0]=='bool'and b==Z:return neg(a[1])
 if b[0]=='bool'and a==Z:return neg(b[1])
 return ('eq',*sorted((a,b),key=repr))
def neg(a):return not a if isinstance(a,bool)else a[1]if a[0]=='not'else('not',a)
def positive(a):return ('lt',Z,a)
class State:
 def __init__(self,words,loop):
  self.words=words;self.loop=loop;self.pc=0;self.reg=[atom('R%02d'%i)for i in range(32)];self.reg[0]=Z;self.reg[29]=num(0x90000);self.initial=self.reg[:];self.fp=[atom('F%02d'%i)for i in range(32)];self.beforefp=self.fp[:];self.lo=Z;self.hi=Z;self.cc=None;self.mem={};self.events=[];self.conditions={};self.steps=[]
 def address(self,rs,imm):return plus(self.reg[rs],num(imm))
 def read(self,a,width):
  if not a[2]and 0x8fff0<=a[1]<0x90000:
   assert width==4 and a in self.mem,(a,width);return self.mem[a]
  key='read%02d/%d'%(len(self.events),width);v=atom(key);self.events.append(('read',a,width,v));return v
 def write(self,a,v,width):
  if not a[2]and 0x8fff0<=a[1]<0x90000:
   assert width==4;self.mem[a]=v
  else:self.events.append(('write',a,width,v))
 def instruction(self,i):
  w=self.words[i];self.steps.append(i);op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn==37:assert self.reg[rt]==Z;self.reg[rd]=self.reg[rs]
   elif fn==33:self.reg[rd]=plus(self.reg[rs],self.reg[rt])
   elif fn==0:self.reg[rd]=scale(self.reg[rt],1<<sa)
   elif fn==25:
    assert not self.reg[rt][2];self.lo=scale(self.reg[rs],self.reg[rt][1])
   elif fn==18:self.reg[rd]=self.lo
   elif fn==42:self.reg[rd]=('bool',('lt',self.reg[rs],self.reg[rt]))
   else:raise AssertionError(('R',i,hex(w)))
  elif op==15:self.reg[rt]=num((w&65535)<<16)
  elif op==9:self.reg[rt]=self.address(rs,imm)
  elif op in(35,36,37,49):
   v=self.read(self.address(rs,imm),{35:4,36:1,37:2,49:4}[op])
   if op==49:self.fp[rt]=v
   else:self.reg[rt]=v
  elif op in(43,57):self.write(self.address(rs,imm),self.reg[rt]if op==43 else self.fp[rt],4)
  elif op==17:
   if rs==4:self.fp[rd]=self.reg[rt]
   elif rs==16 and fn==50:self.cc=('feq',*sorted((self.fp[rd],self.fp[rt]),key=repr))
   else:raise AssertionError(('COP1',i,hex(w)))
  else:raise AssertionError(('op',i,hex(w)))
  self.reg[0]=Z
 def condition(self,w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31
  if op in(4,20):return eq(self.reg[rs],self.reg[rt])
  if op in(5,21):return neg(eq(self.reg[rs],self.reg[rt]))
  if op==7:return positive(self.reg[rs])
  if op==6:return neg(positive(self.reg[rs]))
  if op==17 and rs==8:return self.cc if rt&1 else neg(self.cc)
  return None
 def constrain(self,c,truth):
  if isinstance(c,bool):return c==truth
  if c[0]=='not':c,truth=c[1],not truth
  if c in self.conditions:return self.conditions[c]==truth
  self.conditions[c]=truth;return True
def paths(start,stop_loop):
 todo=[start];done=[]
 while todo:
  m=todo.pop();assert len(m.steps)<200
  if m.pc==m.loop and stop_loop and m.steps:done.append(('loop',m));continue
  i=m.pc;w=m.words[i]
  if w==0x03e00008:
   assert m.reg[31]==m.initial[31];m.instruction(i+1)
   assert m.reg[16:24]==m.initial[16:24]and m.reg[28:]==m.initial[28:]
   assert m.fp[20:]==m.beforefp[20:];done.append(('return',m));continue
  c=m.condition(w)
  if c is not None:
   for take in(True,False):
    n=copy.deepcopy(m)
    if not n.constrain(c,take):continue
    n.steps.append(i)
    likely=w>>26 in(20,21)or(w>>26==17 and(w>>16&2))
    if take or not likely:n.instruction(i+1)
    n.pc=i+1+(((w&65535)^32768)-32768)if take else i+2;todo.append(n)
  else:m.instruction(i);m.pc+=1;todo.append(m)
 return done
def signature(kind,m,raw):
 contract=tuple(m.reg[i]for i in((3,6,2,8,9,11,12,10,16,4,5)if raw else(2,5,3,4,8,9,10,7,16,17,18)))if kind=='loop'else(m.reg[2],)
 return (kind,tuple(sorted(m.conditions.items(),key=repr)),tuple(m.events),contract)
def compare(a,b):
 left=sorted([signature(k,m,True)for k,m in a],key=repr);right=sorted([signature(k,m,False)for k,m in b],key=repr)
 if left!=right:
  (o/'symbolic-mismatch.txt').write_text(repr(left)+'\n\n'+repr(right));raise AssertionError('Symbolic path mismatch')
def proof(raw,retail,write=True):
 starts=[State(raw,27),State(retail,29)];entries=[paths(s,True)for s in starts];assert [len(x)for x in entries]==[3,3];compare(*entries)
 loops=[]
 for n,es in enumerate(entries):
  m=copy.deepcopy(next(m for k,m in es if k=='loop'));assert m.reg[3 if n==0 else 2]==Z
  index=3 if n==0 else 2;cursor=6 if n==0 else 5
  m.reg[index]=atom('INDEX');m.reg[cursor]=plus(m.reg[cursor],scale(atom('INDEX'),2));m.steps=[]
  loops.append(paths(m,True))
 assert[len(x)for x in loops]==[10,10];compare(*loops)
 q=dict(entry_paths=3,inductive_iteration_paths=10,ordered_public_symbolic_accesses_equal=True,all_return_paths_preserve_o32_saved_registers=True,loop_carried_roles_equal=True,scope='32-bit modular leaf operations; public accesses outside private frame; exact ordered reads are fresh symbols, preserving arbitrary public alias dependencies. FP equality is uninterpreted and symmetric; no FCSR/trap model.')
 if write:(o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
