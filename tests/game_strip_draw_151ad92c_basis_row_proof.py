"""Relate an arbitrary entered sample through its second norm comparison."""
from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_strip_draw_151ad92c_basis_proof as relation
from tools.tests import game_strip_draw_151ad92c_entry_proof as opening
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
e,g=opening.e,opening.g
from tools.experiments import game_strip_draw_151ad92c_basis as source
p=source.OUT;INDEX=('SAMPLE_INDEX',);COUNT=e.bitop('AND',('CAPTURED_COUNT',),255)
class State(opening.State):
 def __init__(self,side):
  super().__init__();self.side=side;self.r[29]=('STACK',-304)
  self.r[4],self.r[16],self.r[17]=opening.OUTPUT,opening.RECORD,('CAPTURED_WIDTH',)
  self.r[9]=opening.oracle.SYMS['D_800BE9C0'];self.r[7]=0
  if side=='retail':
   self.r[6]=0;self.r[10]=COUNT;self.r[8]=INDEX;self.r[3]=e.scale(INDEX,24)
   self.r[11]=e.add(INDEX,1);self.r[13]=opening.oracle.TABLE;self.r[31]=12
  else:
   self.r[8]=COUNT;self.r[3]=INDEX;self.r[5]=e.scale(INDEX,24)
   self.r[12]=opening.oracle.TABLE;self.r[13]=12
  self.f=[('ROW_DEAD_FP',side,i)for i in range(32)];self.f[20]=0;self.f[28]=0x40800000
  self.fcsr=('ROW_CSR',);self.condition=('ROW_CONDITION',);self.trace=[]
  for predicate,taken in((e.pred('SLT',INDEX,0),False),(e.pred('SLT',0,COUNT),True),(e.pred('SLT',INDEX,COUNT),True),(e.pred('SLT',COUNT,21),True)):
   e.assume(self,predicate,taken)
def prove(truth,raw):
 terms=Terms();answers=[]
 for side,words in(('retail',truth),('raw',raw)):
  start=(0x151AD9F0-0x151AD92C)if side=='retail'else(0x1B9C-0x1ADC)
  assert words[start//4]>>26==35 and words[start//4]&65535==0x38
  cuts={at:name for at,name in relation.cuts(words).items()if name!='empty'}
  answers.append(opening.Program(words,terms).paths(start,cuts,State(side)))
 left,right=answers;assert left.keys()==right.keys(),('generic path predicates',len(left),len(right))
 for key,a in left.items():
  b=right[key]
  for name,x,y in(('private bytes',a.frame(),b.frame()),('ordered stores and FP status',a.trace,b.trace),('public bytes',a.public,b.public),('stable reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition),('live roles',relation.roles(a,'retail',key[0],truth),relation.roles(b,'raw',key[0],raw))):
   if x!=y:
    at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
    raise AssertionError(('generic first basis',name,at,repr(x[at]if at is not None else x)[:500],repr(y[at]if at is not None else y)[:500]))
 return dict(paths=len(left),arbitrary_entered_sample_index=True,domain='0<=sample<count<=20; mapped disjoint stable record, points, vertices and private frame; nontrapping FP.',all_320_private_bytes=True,ordered_stores_FP_and_status=True,stable_read_multisets=True,live_roles=True,scope='Entered sample through all six first-basis stores and second norm branch; no second basis/backedge claim.',terms=len(terms.values))
