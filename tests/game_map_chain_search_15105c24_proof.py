"""Ordered-read loop induction for the raw/retail two-column list search."""
from pathlib import Path
import json
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
e=g.e;ENTRY=0x15105C24;HEADS=0x800DCE50;COLUMNS=0x800A5770
class State(g.State):
 def __init__(self):super().__init__('common');self.r[4]=('KEY',)
 def load(self,address,size,pool=b''):
  assert not e.tagged(address,'STACK'),('unexpected private read',address)
  value=super().load(address,size,pool);self.trace.append(('READ',address,size,value));return value
 def store(self,address,size,value):raise AssertionError(('unexpected store',address,size))
class Program(g.Program):
 def __init__(self,words,terms,raw):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set();self.raw=raw;self.cut=24*4 if raw else 23*4
 def call(self,s,target):raise AssertionError(('unexpected call',target))

def initial(p,group=None,row=None):
 s=State()
 if group is None:return s
 s.r[6]=('KEY',);s.r[2]=group
 col=e.scale(('LOAD',COLUMNS+group*4,4,0),4);node=('NODE',);kind=e.bitop('AND',('LOAD',e.add(node,0x13),1,0),255)
 if p.raw:s.r[4]=row;s.r[3]=col;s.r[5]=node;s.r[25]=kind;s.r[9]=HEADS;s.r[8]=COLUMNS;s.r[10]=0x2E
 else:s.r[3]=row;s.r[5]=col;s.r[4]=node;s.r[10]=kind;s.r[7]=HEADS;s.r[8]=0x2E
 e.assume(s,e.pred('EQ',node,0),False)
 return s

def observe(s,end,raw):
 assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
 assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
 if end=='return':live=(s.r[2],)
 else:
  assert s.r[6]==('KEY',)and s.r[9 if raw else 7]==HEADS and s.r[10 if raw else 8]==0x2E
  live=(s.r[2],s.r[4 if raw else 3],s.r[3 if raw else 5],s.r[5 if raw else 4],s.r[25 if raw else 10])
 return(s.trace,s.read_set,live)

def prove(raw,retail):
 assert len(raw)==47 and len(retail)==46
 terms=Terms();programs=[Program(raw,terms,True),Program(retail,terms,False)];report={}
 for group,row in[(None,None),*( (a,b)for a in range(2)for b in range(2))]:
  phase='prefix'if group is None else'node-%d-%d'%(group,row);answers=[];counts=[]
  for p in programs:
   paths=p.paths(0 if group is None else p.cut,{p.cut:'node',-4:'return'},initial(p,group,row))
   answers.append({key:observe(s,key[0],p.raw)for key,s in paths.items()});counts.append(max(s.steps for s in paths.values()))
  a,b=answers;assert a.keys()==b.keys(),('path predicates',phase,len(a),len(b))
  for key,x in a.items():
   y=b[key]
   if x!=y:
    part=next(i for i,(left,right)in enumerate(zip(x,y))if left!=right)
    raise AssertionError(('transfer part',phase,part,repr(x[part])[:1800],repr(y[part])[:1800]))
  report[phase]=dict(paths=len(a),max_steps=counts)
 for p,dead in zip(programs,(31*4,30*4)):
  assert p.seen==set(range(0,4*len(p.words),4))-{dead},('coverage',len(p.seen),sorted(set(range(0,4*len(p.words),4))-p.seen))
 return dict(phases=report,covered_words=[len(p.seen)for p in programs],unreachable_next_load_offsets=[124,120],ordered_public_reads=True,no_stores_or_calls=True,all_callee_saved_preserved=True,loop_induction=True,normal_valid_object_domain=True,raw_hardware_fault_or_timing_identity_not_claimed=True)

def negative_controls(raw,retail):
 controls=[]
 for label,index,mask in(('type',6,1),('node-type-offset',23,1),('key-offset',26,4),('next-offset',25,4),('row-bound',36,1),('outer-bound',41,1),('column-scale',11,0x40),('row-stride',17,0x40),('return-node',30,0x00200000)):
  bad=raw[:];bad[index]^=mask
  try:prove(bad,retail)
  except(AssertionError,ValueError,KeyError)as error:
   assert not any(v in str(error).lower()for v in('unsupported','unbounded','out of range')),(label,error)
   controls.append(dict(label=label,reason=repr(error.args)[:400]))
  else:raise AssertionError(('ineffective chain proof control',label))
 return dict(effective_negatives=len(controls),controls=controls)
