from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_strip_draw_151ad92c_entry_proof as entry
g,e=entry.g,entry.e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_strip_draw_151ad92c_basis as source
p=source.OUT
def cuts(words):
 comps=[i for i,w in enumerate(words)if w>>26==17 and w>>21&31==16 and w&63==50];assert len(comps)==2
 first=entry.cuts(words);empty=next(at for at,name in first.items()if name=='empty')
 branch=next(i for i in range(comps[1]+1,len(words))if words[i]>>26==17 and words[i]>>21&31==8)
 target=branch+1+(((words[branch]&65535)^32768)-32768)
 assert words[branch]>>16&1==1
 return {empty:'empty',target*4:'second-zero',(branch+2)*4:'second-nonzero'}
def roles(s,side,end,words):
 common=(s.r[4],s.r[16],s.r[17],s.r[29],s.r[1])
 if end=='empty':return common
 branches=[i for i,w in enumerate(words)if w>>26==17 and w>>21&31==8];assert len(branches)>=2
 address_register=words[branches[1]+1]>>21&31
 if side=='retail':extra=(s.r[10],s.r[8],s.r[3],s.r[11],s.r[13],s.r[31],s.r[9],s.r[address_register])
 else:extra=(s.r[8],s.r[3],s.r[5],s.r[6],s.r[12],s.r[13],s.r[9],s.r[address_register])
 return common+extra+tuple(s.f[i]for i in(0,20,22,24,26,28,30))
def prove(truth,raw):
 terms=Terms();answers=[]
 for side,words in(('retail',truth),('raw',raw)):
  program=entry.Program(words,terms);answers.append(program.paths(0,cuts(words),entry.State()))
 left,right=answers;assert left.keys()==right.keys(),('path predicates',len(left),len(right))
 for key,a in left.items():
  b=right[key]
  for name,x,y in(('all private bytes',a.frame(),b.frame()),('ordered effects and FP status',a.trace,b.trace),('public bytes',a.public,b.public),('public stable reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition),('live roles',roles(a,'retail',key[0],truth),roles(b,'raw',key[0],raw))):
   if x!=y:
    at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
    raise AssertionError(('first-basis relation',key[0],name,at,repr(x[at]if at is not None else x)[:600],repr(y[at]if at is not None else y)[:600]))
 return dict(paths=len(left),ends=dict(Counter(key[0]for key in left)),all_320_private_and_incoming_bytes=True,ordered_public_stores_and_FP_status=True,stable_read_multisets=True,live_roles=True,terms=len(terms.values),scope='Entry through all six first-basis stores and second norm branch; second basis remains open.')
def controls(truth,candidate):
 from tools.tests import game_strip_draw_151ad92c_basis_row_proof as row
 from tools.tests.game_strip_update_151ad174_proof import alternate
 renamed=[alternate(w)for w in candidate];assert renamed!=candidate
 positive=[prove(truth,renamed),row.prove(truth,renamed)]
 changes=[]
 for name,before,after in(('reversed-second-norm-add',0x4608D000,0x461A4000),
                          ('wrong-point-cursor-step',0x24A50018,0x24A5001C),
                          ('narrow-viewport-word',0xAFA60138,0xA7A60138)):
  assert candidate.count(before)==1;changes.append((name,candidate.index(before),after))
 branches=[i for i,w in enumerate(candidate)if w>>26==17 and w>>21&31==8];assert len(branches)==2
 changes.append(('annulled-final-coordinate-store',branches[1],candidate[branches[1]]|2<<16))
 add=candidate.index(0x46124280);sub=candidate.index(0x4602F181)
 # Two independent operations keep their finite values when exchanged, while
 # the required instruction order and abstract FP status must reject them.
 changes.append(('X-subtraction-before-Z-addition',add,None))
 controls=[]
 for name,index,replacement in changes:
  bad=candidate[:]
  if replacement is None:bad[add],bad[sub]=bad[sub],bad[add]
  else:assert bad[index]!=replacement;bad[index]=replacement
  outcomes=[]
  phases=(('entry',prove),)if name=='narrow-viewport-word'else(('entry',prove),('generic',row.prove))
  for phase,check in phases:
   try:check(truth,bad)
   except AssertionError as error:
    reason=str(error);assert not any(s in reason for s in('unsupported','unbounded','escaped code')),reason
    outcomes.append(dict(phase=phase,rejected=reason[:240]))
   else:raise AssertionError(('ineffective first-basis control',name,phase))
  controls.append(dict(name=name,index=index,outcomes=outcomes))
 return dict(independent_GPR_allocation_positive=positive,effective_controls=controls)
