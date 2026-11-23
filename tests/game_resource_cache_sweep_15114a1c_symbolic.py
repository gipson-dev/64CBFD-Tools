"""Independent instruction interpreter: live-loop bisimulation, no projection input."""
import copy,json
from tools.experiments import game_resource_cache_sweep_15114a1c_match as p
from tools.tests.game_group_record_pairs_15022024_symbolic import atom,num,plus,scale,eq,neg,Z
ENTRY=0x15114A1C;STACK=0x90000
class State:
 def __init__(self,words,loop):
  self.words=words;self.loop=loop;self.pc=0;self.reg=[atom('R%02d'%i)for i in range(32)];self.reg[0]=Z;self.reg[29]=num(STACK);self.initial=self.reg[:];self.mem={};self.events=[];self.conditions={};self.steps=[]
 def read(self,a,n):
  if not a[2]and STACK-64<=a[1]<STACK:
   assert n==4 and a in self.mem;return self.mem[a]
  v=atom('read%02d/%d'%(len(self.events),n));self.events.append(('read',a,n,v));return v
 def write(self,a,v,n):
  if not a[2]and STACK-64<=a[1]<STACK:assert n==4;self.mem[a]=v
  else:self.events.append(('write',a,n,('low',n,v)if n<4 else v))
 def ins(self,i):
  self.steps.append(i);w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn==37:assert self.reg[rt]==Z;self.reg[rd]=self.reg[rs]
   elif fn==33:self.reg[rd]=plus(self.reg[rs],self.reg[rt])
   elif fn==0:self.reg[rd]=scale(self.reg[rt],1<<sa)
   elif fn==42:self.reg[rd]=('bool',('lt',self.reg[rs],self.reg[rt]))
   else:raise AssertionError(('R',i,hex(w)))
  elif op==15:self.reg[rt]=num((w&65535)<<16)
  elif op==9:self.reg[rt]=plus(self.reg[rs],num(imm))
  elif op==12:self.reg[rt]=('and',self.reg[rs],w&65535)
  elif op in(35,36):self.reg[rt]=self.read(plus(self.reg[rs],num(imm)),4 if op==35 else 1)
  elif op in(43,40):self.write(plus(self.reg[rs],num(imm)),self.reg[rt],4 if op==43 else 1)
  else:raise AssertionError(('op',i,hex(w)))
  self.reg[0]=Z
 def condition(self,w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31
  if op in(4,20):return eq(self.reg[rs],self.reg[rt])
  if op in(5,21):return neg(eq(self.reg[rs],self.reg[rt]))
  if op==6:return neg(('lt',Z,self.reg[rs]))
  return None
 def constrain(self,c,truth):
  if isinstance(c,bool):return c==truth
  if c[0]=='not':c,truth=c[1],not truth
  if c in self.conditions:return self.conditions[c]==truth
  self.conditions[c]=truth;return True
 def call(self,target):
  assert target==0x10004074,hex(target)
  self.events.append(('call',target,(self.reg[4],)))
  for reg in(1,2,3,*range(4,16),24,25):self.reg[reg]=atom('call%02d/R%d'%(len(self.events),reg))
  # Each subsequent public read is an unconstrained fresh symbol, including
  # alias effects from any preceding public write or opaque provider.
def paths(start,stop=True):
 todo=[start];done=[]
 while todo:
  m=todo.pop();assert len(m.steps)<180
  if m.pc==m.loop and stop and m.steps:done.append(('loop',m));continue
  i=m.pc;w=m.words[i]
  if w==0x03e00008:
   assert m.reg[31]==m.initial[31];m.ins(i+1)
   assert m.reg[16:24]==m.initial[16:24]and m.reg[28:]==m.initial[28:]
   done.append(('return',m));continue
  if w>>26==3:
   m.steps.append(i);m.reg[31]=num(ENTRY+4*i+8);m.ins(i+1);m.call(((ENTRY+4*i+4)&0xf0000000)|((w&0x3ffffff)<<2));m.pc=i+2;todo.append(m);continue
  c=m.condition(w)
  if c is not None:
   for take in(True,False):
    n=copy.deepcopy(m)
    if not n.constrain(c,take):continue
    n.steps.append(i)
    if take or w>>26 not in(20,21):n.ins(i+1)
    n.pc=i+1+(((w&65535)^32768)-32768)if take else i+2;todo.append(n)
  else:m.ins(i);m.pc+=1;todo.append(m)
 return done
def signature(kind,m,raw):
 live=(17,19,18,20,21,22,23,5)if raw else(16,20,18,22,21,23,30,4)
 return(kind,tuple(sorted(m.conditions.items(),key=repr)),tuple(m.events),tuple(m.reg[i]for i in live)if kind=='loop'else())
def compare(left,right):
 a=sorted((signature(k,m,True)for k,m in left),key=repr);b=sorted((signature(k,m,False)for k,m in right),key=repr)
 if a!=b:
  (p.OUT/'symbolic-mismatch.txt').write_text(repr(a)+'\n\n'+repr(b));raise AssertionError('Cache sweep symbolic path mismatch')
def proof(raw,retail,write=True):
 assert len(raw)==92 and len(retail)==94
 entries=[paths(State(raw,23)),paths(State(retail,24))];compare(*entries)
 loops=[]
 for j,es in enumerate(entries):
  m=copy.deepcopy(next(m for kind,m in es if kind=='loop'));index,offset,count=(17,19,5)if j==0 else(16,20,4)
  m.reg[index]=atom('INDEX');m.reg[offset]=atom('OFFSET');m.reg[count]=atom('COUNT');m.steps=[];m.events=[];m.conditions={};loops.append(paths(m))
 compare(*loops)
 q=dict(entry_paths=len(entries[0]),inductive_iteration_paths=len(loops[0]),ordered_public_reads_writes_and_opaque_call_arguments_equal=True,arbitrary_live_count_tables_and_public_alias_effects=True,all_o32_saved_registers_restore=True,scope='Normal executions with mapped ordinary public RAM disjoint from the owned private frame and a returning o32 provider. Modular emitted integer operations; void result, private dead bytes and raw fault-prefix identity are not portable C claims.')
 if write:(p.OUT/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
