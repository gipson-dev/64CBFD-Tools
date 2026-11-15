"""Conditional one-emission transfer with strict ordered FP/FCSR and ABI calls."""
from copy import deepcopy
from pathlib import Path
import json
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g

def bounds(v):
 if isinstance(v,int):return v,v
 if e.tagged(v,'LOAD'):return 0,(1<<(8*v[2]))-1
 if e.tagged(v,'LINEAR'):
  low=high=v[1]
  for item,k in v[2]:
   a,b=bounds(item);assert k<0x80000000
   low+=a*k;high+=b*k
  assert high<=0xFFFFFFFF;return low,high
 raise AssertionError(('no integer interval',v))

class State(e.State):
 def __init__(self,side):
  super().__init__('common','core');self.side=side;self.r[29]=('STACK',-280);self.mem={};self.effects=[];self.private_writes=[]
  self.r[17]=('EFFECT',);self.r[19]=('PAYLOAD',);self.r[20]=('ACTOR',);self.r[3]=36;self.r[7]=('ENTRIES',);self.r[11]=('STACK',-112);self.r[1]=('VELOCITY_X',)
  self.lo=e.scale(('CURSOR',),36);self.r[25]=('CURSOR',);self.r[16]=('OLD_ENTRY',)
  if side=='raw':self.r[12]=('STACK',-112);self.r[8]=('CURSOR',)
  self.fcsr=('LIVE_FCSR',);self.fp=[];self.fp_condition=None
  self.f[20]=('REMAINING',);self.f[22]=('WEIGHT',);self.f[28]=0x3F800000
  self.f[26]=('BOUND',);self.f[24]=0x42C80000
  self.mem[-112]=('VELOCITY_X',);self.mem[-108]=('VELOCITY_Z',)
  for i in range(3):self.mem[-80+4*i]=('POSITION',i)
 def load(self,address,size,pool):
  if not e.tagged(address,'STACK'):return super().load(address,size,pool)
  assert size==4 and address[1]%4==0 and address[1] in self.mem,('core private load',address,size)
  return self.mem[address[1]]
 def store(self,address,size,value):
  if not e.tagged(address,'STACK'):
   super().store(address,size,value);self.effects.append(self.trace[-1]);return
  assert size==4 and address[1]%4==0;self.mem[address[1]]=value;self.private_writes.append((address[1],size))

class Program(e.Program):
 def __init__(self,words,terms,side):super().__init__(words,b'',g.ENTRY);self.terms=terms;self.side=side
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==4:s.f[w>>11&31]=s.r[w>>16&31]
  elif op==17 and fmt==16 and fn in (0,1,2,5,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;args=(s.f[fs],) if fn==5 else(s.f[fs],s.f[ft]);event=(fn,args,s.fcsr);s.fp.append(event);s.effects.append(('FP',event))
   value=self.terms.term('FP_VALUE',*event);s.fcsr=self.terms.term('FP_STATUS',*event)
   if fn==60:s.fp_condition=value
   else:s.f[fd]=value
  elif op==0 and fn==27:
   a,b=s.r[w>>21&31],s.r[w>>16&31];low,high=bounds(b);assert 1<=low<=high<=256,('unproved nonzero byte divisor',low,high)
   s.lo=('UDIV',a,b);s.hi=('UREM',a,b)
  else:super().step(s,w)
 def call(self,s,target):
  assert target in (g.RNG,g.FLOOR) and s.r[29]==('STACK',-280)
  args=tuple(s.r[4:8]) if target==g.FLOOR else()
  if target==g.FLOOR:
   assert args[0]==('STACK',-140) and args[1]==0 and args[3]==e.add(('EFFECT',),96),('floor query interface changed',args)
   point=tuple(s.load(('STACK',-140+4*i),4,b'') for i in range(3))
   s.trace.append(('QUERY',target,args,point,s.fcsr))
  else:s.trace.append(('CALL',target,args,s.fcsr))
  s.effects.append(s.trace[-1])
  ordinal=s.calls[target];s.calls[target]+=1
  for i in (1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',target,ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',target,ordinal,i)
  for i in range(4):s.mem[-280+4*i]=('CALL_HOME',target,ordinal,i)
  if target==g.FLOOR:
   for i in range(3):s.mem[-140+4*i]=('QUERY_POINT_AFTER',ordinal,i)
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',target,ordinal)
  s.hi=('CALL_HI',target,ordinal);s.lo=('CALL_LO',target,ordinal);s.fcsr=('CALL_FCSR',target,ordinal)
 def paths(self):
  states=[(0x3F4,State(self.side))];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1;assert work<20000 and s.steps<200,('core proof bound',pc)
   if pc==0x558:
    key=tuple(sorted(s.facts.items(),key=repr));assert key not in answers;answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
   if floating or op in (4,5,20,21):
    if floating:condition=s.fp_condition
    else:
     x,y=s.r[rs],s.r[rt];condition=e.pred('EQ',x,y)
     if y==0 and not isinstance(x,int):
      try:low,high=bounds(x)
      except AssertionError:pass
      else:
       if low>0:condition=False
    if (floating and not rt&1) or op in (5,21):condition=e.negate(condition)
    likely=bool(rt&2) if floating else op in (20,21)
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:self.step(n,self.instruction(pc+4))
     target=pc+4+4*(((w&65535)^32768)-32768) if taken else pc+8;states.append((target,n))
   elif op==3:
    self.step(s,self.instruction(pc+4));self.call(s,((self.entry+pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));states.append((pc+8,s))
   else:self.step(s,w);states.append((pc+4,s))
  return answers

def normalized_trace(s):
 trace=s.trace[:];entry=e.add(('ENTRIES',),e.scale(('CURSOR',),36))
 xread=('READ',entry,4);z=e.add(entry,4)
 # The second X read occurs after X has been stored. Its only crossed public
 # write is Z at entry+4, a disjoint four-byte field at the same stable base.
 inds=[i for i,v in enumerate(trace) if v==xread];assert len(inds)==2
 i=inds[1];j=next(k for k,v in enumerate(trace) if k>inds[0] and v[0]=='WRITE' and v[1]==z)
 assert abs(i-j)==1,(i,j,trace)
 if i<j:trace[i:j+1]=[trace[j],trace[i]]
 # Ordinary adjacent threshold/actor-height reads have no intervening write,
 # provider or FP operation. Both execute before the same C.LT.S.
 threshold=('READ',g.symbols()['D_800A8CFC'],4);height=('READ',e.add(('ACTOR',),0x118),4)
 i,j=trace.index(threshold),trace.index(height);assert abs(i-j)==1,(i,j,trace)
 trace[min(i,j):max(i,j)+1]=[threshold,height]
 return trace
def relation(s):
 assert all(size==4 and off in (-140,-136,-132) for off,size in s.private_writes),('core overwrote protected frame home',s.private_writes)
 assert s.r[29]==('STACK',-280)
 live=(s.r[16],s.r[17],s.r[18],s.r[19],s.r[20],s.f[20],s.f[22],s.f[28],s.f[26],s.f[24])
 assert all(s.r[i]==('ENTRY',i) for i in (21,22,23,28,30))
 return s.effects,normalized_trace(s),s.fp,s.fcsr,live
def prove(raw,retail):
 terms=Terms();a=Program(raw,terms,'raw').paths();b=Program(retail,terms,'retail').paths()
 assert a.keys()==b.keys(),('core path predicates',len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
 for key in a:
  x,y=relation(a[key]),relation(b[key]);assert x==y,('core transfer',key,x,y)
 return dict(symbolic_paths=len(a),arbitrary_live_FP_words=True,ordered_FP_and_FCSR=True,opaque_RNG_and_query=True,
             nonzero_divisor_interval=[1,256],complete_initialized_query_point=True,closed_ordinary_memory_commutes=2,
             whole_function=False,raw_fault_state_claimed=False)
