"""Symbolic accepted-ring update and loop tail with strictly ordered FP/FCSR."""
from copy import deepcopy
from pathlib import Path
import json
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g

class State(e.State):
 def __init__(self,side):
  super().__init__('common','tail');self.side=side;self.r[29]=('STACK',-280);self.mem={};self.effects=[];self.private_writes=[]
  self.r[16]=('ENTRY_RECORD',);self.r[17]=('EFFECT',);self.r[19]=('PAYLOAD',);self.r[20]=('ACTOR',);self.r[18]=('ACCEPTED',)
  self.fcsr=('LIVE_FCSR',);self.fp=[];self.fp_condition=None
  self.f[20]=('REMAINING',);self.f[22]=('WEIGHT',);self.f[28]=0x3F800000
  self.f[26]=('BOUND',);self.f[24]=0x42C80000
  for i in range(3):self.mem[-80+4*i]=('POSITION',i)
  for off,name in zip((0x74,0x70,0x6C,0x68) if side=='raw' else (0x7C,0x78,0x74,0x70),('STEP_X','STEP_Y','STEP_Z','STEP_WEIGHT')):self.mem[off-280]=(name,)
  self.mem[-64]=('STEP_TIME',);self.mem[(0x80 if side=='raw' else 0x84)-280]=e.add(('PAYLOAD',),16)
  self.mem[-8]=('ENTRIES',);self.mem[-112]=('VELOCITY_X',);self.mem[-108]=('VELOCITY_Z',)
 def load(self,address,size,pool):
  if not e.tagged(address,'STACK'):return super().load(address,size,pool)
  assert size==4 and address[1]%4==0
  assert address[1] in self.mem,('uninitialized tail private home',self.side,address)
  return self.mem[address[1]]
 def store(self,address,size,value):
  if not e.tagged(address,'STACK'):
   super().store(address,size,value);self.effects.append(self.trace[-1]);return
  assert size==4 and address[1]%4==0;self.mem[address[1]]=value;self.private_writes.append((address[1],size))

class Program(e.Program):
 def __init__(self,words,terms):super().__init__(words,b'',g.ENTRY);self.terms=terms
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in (0,1,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;args=(s.f[fs],s.f[ft]);event=(fn,args,s.fcsr);s.fp.append(event);s.effects.append(('FP',event))
   value=self.terms.term('FP_VALUE',*event);s.fcsr=self.terms.term('FP_STATUS',*event)
   if fn==60:s.fp_condition=value
   else:s.f[fd]=value
  else:super().step(s,w)
 def paths(self):
  states=[(0x558,State(self.side))];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1;assert work<20000 and s.steps<200,('tail proof bound',pc)
   if pc in (0x3F4,0x648):
    key=('loop' if pc==0x3F4 else 'return',tuple(sorted(s.facts.items(),key=repr)));assert key not in answers;answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
   if floating or op in (4,5,20,21):
    condition=s.fp_condition if floating else e.pred('EQ',s.r[rs],s.r[rt])
    if (floating and not rt&1) or op in (5,21):condition=e.negate(condition)
    likely=bool(rt&2) if floating else op in (20,21)
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:self.step(n,self.instruction(pc+4))
     target=pc+4+4*(((w&65535)^32768)-32768) if taken else pc+8
     states.append((target,n))
   else:self.step(s,w);states.append((pc+4,s))
  return answers

def relation(s,label):
 assert all(size==4 and off in (-80,-76,-72) for off,size in s.private_writes),('tail overwrote protected frame home',s.private_writes)
 assert s.r[29]==('STACK',-280)
 assert (s.r[17],s.r[19],s.r[20])==(('EFFECT',),('PAYLOAD',),('ACTOR',)),('tail changed loop owner roots',s.r[17],s.r[19],s.r[20])
 assert all(s.r[i]==('ENTRY',i) for i in (21,22,23,28,30))
 live=(s.f[20],s.f[22],s.f[28],s.f[26],s.f[24],tuple(s.mem[-80+4*i] for i in range(3)))
 if label=='loop':
  assert s.r[3]==36 and s.r[7]==('ENTRIES',) and s.r[12 if s.side=='raw' else 11]==('STACK',-112) and s.r[1]==('VELOCITY_X',)
  live+=(s.lo,s.r[8 if s.side=='raw' else 25],s.r[3],s.r[7],s.r[12 if s.side=='raw' else 11],s.r[1])
 else:assert s.r[2]==1
 return s.effects,s.trace,s.fp,s.fcsr,live
def prove(raw,retail):
 terms=Terms();a=Program(raw,terms);a.side='raw';b=Program(retail,terms);b.side='retail'
 left,right=a.paths(),b.paths();assert left.keys()==right.keys(),('tail path predicates',len(left),len(right),list(left.keys()-right.keys())[:1])
 for key in left:
  x,y=relation(left[key],key[0]),relation(right[key],key[0]);assert x==y,('tail transfer',key,x,y)
 return dict(symbolic_paths=len(left),arbitrary_live_FP_words=True,ordered_FP_and_FCSR=True,ring_wrap_and_count=True,
             loop_boundary_arguments_equal=True,private_spill_relation=True,whole_function=False,raw_fault_state_claimed=False)
