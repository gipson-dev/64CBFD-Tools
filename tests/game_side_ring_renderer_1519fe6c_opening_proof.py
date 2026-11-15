"""Instruction-driven entry and inductive fade-loop proof; geometry stays open.

Ordinary public reads are stable within a memory epoch. Every public store or
opaque provider starts a fresh epoch, allowing arbitrary public aliases and
provider mutations. Private stack and implementation code are inaccessible to
public pointers/providers except the allocator's exact exposed four-byte slot.
This is normal-execution equivalence, not raw fault-register or hardware proof.
"""
from copy import deepcopy
from pathlib import Path
import json,struct
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_side_ring_emitter_1519f7f0_transition_proof import byte,word
from tools.experiments import game_side_ring_renderer_1519fe6c_recovery as source
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

class State(e.State):
 def __init__(self,side,phase):
  super().__init__('common',phase);self.side=side;self.phase=phase
  self.mem={};self.epoch=0;self.private_writes=[]
  self.r[29]=('STACK',0);self.r[31]=('RETURN',)
  self.r[4]=('EFFECT',);self.r[5]=('OUTPUT',);self.r[6]=('VIEW',)
  self.r[16]=('ENTRY',16)
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):
   assert size in (1,2,4) and address[1]%size==0
   values=[self.mem.get(address[1]+i,('PRIVATE_BYTE',address[1]+i)) for i in range(size)]
   return values[0] if size==1 else word(values) if size==4 else ('HALF',tuple(values))
  e.plain(address);self.trace.append(('READ',address,size))
  return ('LOAD',address,size,self.epoch)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   assert size in (1,2,4) and address[1]%size==0
   self.private_writes.append((address[1],size))
   for i in range(size):self.mem[address[1]+i]=byte(value,8*(size-i-1))
  else:
   e.plain(address);e.plain(value)
   self.trace.append(('WRITE',address,size,e.bitop('AND',value,(1<<(8*size))-1)))
   self.epoch+=1

class Program(e.Program):
 def __init__(self,words):super().__init__(words,b'',g.ENTRY)
 def step(self,s,w):
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op in (53,61):
   address=e.add(s.r[rs],e.signed((w&65535)|(-65536 if w&32768 else 0)))
   assert e.tagged(address,'STACK') and address[1]%8==0
   if op==61:s.store(address,4,s.f[rt]);s.store(e.add(address,4),4,s.f[rt+1])
   else:s.f[rt]=s.load(address,4,b'');s.f[rt+1]=s.load(e.add(address,4),4,b'')
  else:super().step(s,w)
 def call(self,s,target):
  assert target==g.BACKEND and s.r[29]==('STACK',-240)
  args=tuple(s.r[4:8])+tuple(s.load(e.add(s.r[29],16+4*i),4,b'') for i in range(1))
  assert args[3]==('STACK',-4) and args[4]==0,('allocator exposed home',args[3:])
  s.trace.append(('CALL',target,args,s.fcsr));ordinal=s.calls[target];s.calls[target]+=1;s.epoch+=1
  for i in (1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',target,ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',target,ordinal,i)
  for i in range(4):s.store(('STACK',-240+4*i),4,('CALL_HOME',target,ordinal,i))
  s.store(('STACK',-4),4,('VERTICES',));s.r[2]=('RESULT',target,ordinal)
  s.r[31]=('CALL_RETURN',target,ordinal);s.hi=('CALL_HI',target,ordinal);s.lo=('CALL_LO',target,ordinal);s.fcsr=('CALL_FCSR',target,ordinal)
 def paths(self,start,stops,initial):
  states=[(start,initial)];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1
   assert work<10000 and s.steps<200,('unbounded proof',start,len(answers),hex(pc))
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)))
    assert key not in answers,('duplicate proof path',key)
    answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
   delay=lambda state:self.step(state,self.instruction(pc+4))
   if op in(1,4,5,6,7,20,21,22,23):
    if op==1:
     assert rt in (0,1,2,3);condition=e.pred('SLT',s.r[rs],0)
     if rt in(1,3):condition=e.negate(condition)
     likely=rt in(2,3)
    else:
     if op in(4,5,20,21):condition=e.pred('EQ',s.r[rs],s.r[rt])
     else:assert rt==0;condition=e.pred('SLT',0,s.r[rs])
     if op in(5,21,6,22):condition=e.negate(condition)
     likely=op>=20
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:delay(n)
     dest=pc+4+4*e.signed((w&65535)|(-65536 if w&32768 else 0)) if taken else pc+8
     states.append((dest,n))
   elif op==3:
    s.r[31]=self.entry+pc+8;delay(s);self.call(s,((self.entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2));states.append((pc+8,s))
   elif op==0 and w&63==8:
    assert s.r[rs]==('RETURN',);delay(s);states.append((-4,s))
   else:self.step(s,w);states.append((pc+4,s))
  return answers

SAVED={'raw':{16:-172,17:-168,18:-164,19:-160},'retail':{16:-168,17:-164,18:-160}}
FP={'raw':-192,'retail':-184}
CUTS={'raw':{0xB4:'forward',0x134:'backward',0x194:'graphics',-4:'return'},'retail':{0xAC:'forward',0x12C:'backward',0x18C:'graphics',-4:'return'}}

def saved(s):
 for reg,off in SAVED[s.side].items():assert s.load(('STACK',off),4,b'')==('ENTRY',reg),('saved GPR',s.side,reg)
 for i in range(4):assert s.load(('STACK',FP[s.side]+4*i),4,b'')==('ENTRY_FP',20+i),('saved FPR',s.side,i)
 assert s.load(('STACK',-156),4,b'')==('RETURN',)
 assert s.r[29]==('STACK',-240)
 assert all(s.r[i]==('ENTRY',i) for i in (20,21,22,23,28,30))
 if s.side=='retail':assert s.r[19]==('ENTRY',19)

def initial(side,phase):
 s=State(side,phase)
 if phase=='prefix':return s
 s.r[29]=('STACK',-240);s.r[16]=('OUTPUT',);s.r[17]=('EFFECT',)
 for reg,off in SAVED[side].items():s.store(('STACK',off),4,('ENTRY',reg))
 for i in range(4):s.store(('STACK',FP[side]+4*i),4,('ENTRY_FP',20+i))
 s.store(('STACK',-156),4,('RETURN',));s.store(('STACK',-4),4,('VERTICES',));s.store(('STACK',-95),1,1)
 s.r[10 if side=='raw'else 9]=('PACKET',);s.r[18 if side=='raw'else 12]=('RECORDS',)
 s.r[19 if side=='raw'else 18]=36;s.r[7]=0
 if phase=='forward':s.r[2]=('INDEX',);s.r[4]=('REMAINING',);s.r[5]=('FACTOR',)
 else:s.r[4 if side=='raw'else 2]=('INDEX',);s.r[5]=('REMAINING',);s.r[6]=('FACTOR',)
 s.private_writes=[];return s

def relation(s,end):
 allowed={-240,-236,-232,-228,-224,-4,-95,8,-156,*SAVED[s.side].values(),*(FP[s.side]+4*i for i in range(4))}
 assert all((off in allowed and size==(1 if off==-95 else 4)) for off,size in s.private_writes),('opening private write escape',s.side,s.private_writes)
 if end=='return':
  assert s.r[29]==('STACK',0) and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i) for i in (16,17,18,19,20,21,22,23,28,30))
  assert tuple(s.f[20:])==tuple(('ENTRY_FP',i) for i in range(20,32))
  return s.trace,s.r[2],s.fcsr,tuple(s.f[20:])
 saved(s)
 common=(s.trace,s.fcsr,s.r[16],s.r[17],s.load(('STACK',-4),4,b''),s.load(('STACK',-95),1,b''),s.r[10 if s.side=='raw'else 9],s.r[18 if s.side=='raw'else 12],s.r[7],tuple(s.f[20:]))
 if end=='graphics':return common
 stride=s.r[19 if s.side=='raw'else 18];assert stride==36
 if end=='forward':live=(s.r[2],s.r[4],s.r[5])
 else:live=(s.r[4 if s.side=='raw'else 2],s.r[5],s.r[6])
 return common,live

def prove(raw,retail):
 reports={}
 for phase in ('prefix','forward','backward'):
  paths={}
  for side,words in (('raw',raw),('retail',retail)):
   start=0 if phase=='prefix' else next(pc for pc,name in CUTS[side].items() if name==phase)
   paths[side]=Program(words).paths(start,CUTS[side],initial(side,phase))
  a,b=paths['raw'],paths['retail']
  assert a.keys()==b.keys(),('path predicates',phase,len(a),len(b),next(iter(a.keys()-b.keys()),None),next(iter(b.keys()-a.keys()),None))
  for key in a:
   left,right=relation(a[key],key[0]),relation(b[key],key[0])
   assert left==right,('opening transfer',phase,key,left,right)
  reports[phase]=len(a)
 return dict(inductive_symbolic_paths=reports,complete_entry_and_all_fade_iterations=True,ordinary_memory_epochs_invalidated_on_every_public_store_and_provider=True,exposed_allocator_home=-4,sync_home=-95,geometry_proved=False,whole_function=False,c_match_credit=0)

def main():
 out=source.OUT;programs=g.programs();raw=programs['candidate'];retail=programs['retail']
 report=prove(raw,retail)
 def swap(w):
  op,fn=w>>26,w&63
  if op==0:fields=(16,11) if fn in(0,2,3) else (21,16,11) if fn in(33,35,36,37,42,43) else (11,) if fn in(16,18) else (21,16) if fn==25 else (21,) if fn==8 else ()
  elif op in(3,53,61):fields=(21,) if op in(53,61) else ()
  elif op==15:fields=(16,)
  else:fields=(21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(14,15):w=(w&~(31<<shift))|((29-reg)<<shift)
  return w
 alternative=[swap(w) for w in raw];assert alternative!=raw and prove(alternative,retail)==report
 report['independent_scratch_allocation_positive_control']=True
 controls=[]
 for name,pc,change in (
  ('signed-count',0x38,lambda w:w^(4<<26)),
  ('allocator-exposed-home',0x70,lambda w:w-4),
  ('forward-index',0xB8,lambda w:(w&0xFFFF0000)|2),
  ('forward-count',0xBC,lambda w:w-1),
  ('light-field',0xC8,lambda w:w-2),
  ('factor-byte-wrap',0xDC,lambda w:w^0x80),
  ('backward-initial-wrap',0x130,lambda w:w-1),
  ('backward-count',0x138,lambda w:w-1),
  ('signed-counter-narrowing',0x164,lambda w:w^(1<<6)),
  ('backward-light-scale',0x154,lambda w:w^(1<<6))):
  wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
  try:prove(wrong,retail)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in('unsupported','unbounded proof','escaped code')),('invalid control',name,reason)
   controls.append(dict(name=name,rejected=reason[:180]))
  else:raise AssertionError(('ineffective proof control',name))
 report['effective_controls']=controls
 (out/'opening-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
