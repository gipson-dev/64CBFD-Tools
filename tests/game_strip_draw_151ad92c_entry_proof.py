"""Partial symbolic relation through the first norm; no whole-function credit."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct,sys
from tools.tests import game_strip_update_151ad174_proof as reuse
from tools.tests import game_strip_draw_151ad92c_private_oracle as oracle
from tools.experiments import game_strip_draw_151ad92c_lifetime as source
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
g,e=reuse.g,reuse.e
p=source.OUT;ENTRY=source.ENTRY;FRAME=304
RECORD,POINTS,OUTPUT=('RECORD',),('POINTS',),('OUTPUT',)
class State(g.State):
 def __init__(self):
  super().__init__('common');self.side='common';self.phase='prefix';self.mem={i:('PRIVATE_ENTRY',i)for i in range(-FRAME,16)}
  self.public={};self.read_set=Counter();self.epoch=0;self.trace=[]
  self.r=[0]+[('ENTRY_GPR',i)for i in range(1,32)]
  self.r[4],self.r[5],self.r[6],self.r[29],self.r[31]=OUTPUT,RECORD,('VIEWPORT',),('STACK',0),('RETURN',)
  self.f=[('ENTRY_FP',i)for i in range(32)];self.fcsr=('ENTRY_CSR',);self.condition=('ENTRY_CONDITION',)
  self.store(e.add(RECORD,0x38),4,POINTS);self.trace=[]
 def load(self,address,size,pool=b''):
  assert size in(1,2,4)
  if e.tagged(address,'STACK'):
   at=address[1];assert -FRAME<=at and at+size<=16 and at%size==0
   return g.join([self.mem[at+i]for i in range(size)])
  value=g.join([self.public.get(e.add(address,i),('MEMORY_BYTE',e.add(address,i)))for i in range(size)])
  self.read_set[address,size,value]+=1;return value
 def store(self,address,size,value):
  assert size in(1,2,4)
  if e.tagged(address,'STACK'):
   at=address[1];assert -FRAME<=at and at+size<=16 and at%size==0
   for i in range(size):self.mem[at+i]=g.byte(value,8*(size-i-1))
  else:
   self.trace.append(('WRITE',address,size,value))
   for i in range(size):self.public[e.add(address,i)]=g.byte(value,8*(size-i-1))
 def frame(self):return tuple(self.mem[i]for i in range(-FRAME,16))
class Program(reuse.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
def derive(words):
 result=words[:];edits=[]
 for i,word in enumerate(words):
  if word>>26 in(35,43)and word>>21&31==29 and word&65535 in(0x120,0x124):
   old=word&65535;new={0x120:0x118,0x124:0x11C}[old];result[i]=word&0xFFFF0000|new
   edits.append(dict(index=i,expected_word=word,replacement_word=result[i],source_home=old,destination_home=new))
 assert len(edits)>=3 and {v['source_home']for v in edits}=={0x120,0x124}
 return result,edits
def cuts(words):
 compare=next(i for i,w in enumerate(words)if w>>26==17 and w>>21&31==16 and w&63==50)
 branch=next(i for i,w in enumerate(words[:compare])if w>>26==6)
 setup=branch+1+(((words[branch]&65535)^32768)-32768)
 assert setup>compare
 return {setup*4:'empty',compare*4+4:'norm'}
def roles(s,side,end,words):
 common=(s.r[4],s.r[16],s.r[17],s.r[29])
 if end=='empty':return common
 if side=='retail':extra=(s.r[10],s.r[8],s.r[3],s.r[11],s.r[13],s.r[31],s.r[9],s.f[18])
 else:
  root=next(i for i,w in enumerate(words)if w>>26==17 and w>>21&31==16 and w&63==4)
  squares=[w for w in words[:root]if w>>26==17 and w>>21&31==16 and w&63==2]
  assert len(squares)==2 and squares[-1]>>16&31==squares[-1]>>11&31
  dz_register=squares[-1]>>11&31
  extra=(s.r[8],s.r[3],s.r[5],s.r[6],s.r[12],s.r[13],s.r[9],s.f[dz_register])
 return common+extra+tuple(s.f[i]for i in(0,20,22,24,26,28,30))
def prove(truth,raw):
 terms=Terms();answers=[]
 for side,words in(('retail',truth),('raw',raw)):
  program=Program(words,terms);answers.append(program.paths(0,cuts(words),State()))
 left,right=answers;assert left.keys()==right.keys(),('path predicates',len(left),len(right))
 for key,a in left.items():
  b=right[key]
  for name,x,y in(('all private bytes',a.frame(),b.frame()),('ordered effects and FP status',a.trace,b.trace),('public bytes',a.public,b.public),('public stable reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition),('live roles',roles(a,'retail',key[0],truth),roles(b,'raw',key[0],raw))):
   if x!=y:
    at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
    raise AssertionError(('prefix relation',key[0],name,at,repr(x[at]if at is not None else x)[:450],repr(y[at]if at is not None else y)[:450]))
 return dict(paths=len(left),ends=dict(Counter(key[0]for key in left)),all_320_private_and_incoming_bytes=True,ordered_FP_and_abstract_status=True,stable_read_multisets=True,live_roles=True,terms=len(terms.values),scope='Entry through first norm comparison or empty setup boundary only.')
def controls(truth,candidate,edits):
 renamed=[reuse.alternate(word)for word in candidate];assert renamed!=candidate
 positive=prove(truth,renamed);bad=[];limit=max(cuts(candidate))
 for row in edits:
  if row['index']*4<limit:bad.append(('wrong-opening-home-'+str(row['index']),row['index'],row['expected_word']))
 for name,before,after in(('wrong-next-X-stride',0xC4440018,0xC444001C),('narrow-viewport-home',0xAFA60138,0xA7A60138)):
  assert candidate.count(before)==1;bad.append((name,candidate.index(before),after))
 neg=next(i for i,w in enumerate(candidate)if w>>26==17 and w>>21&31==16 and w&63==7)
 bad.append(('absolute-instead-of-negative',neg,candidate[neg]&~63|5))
 root=next(i for i,w in enumerate(candidate)if w>>26==17 and w>>21&31==16 and w&63==4)
 add=root-1;word=candidate[add];assert word>>26==17 and word&63==0
 ft,fs=word>>16&31,word>>11&31
 bad.append(('norm-addition-operand-order',add,word&~((31<<16)|(31<<11))|fs<<16|ft<<11))
 rejected=[]
 for name,index,replacement in bad:
  changed=candidate[:];assert changed[index]!=replacement;changed[index]=replacement
  try:prove(truth,changed)
  except AssertionError as error:
   reason=str(error);assert not any(s in reason for s in('unsupported','unbounded','escaped code')),reason
   rejected.append(dict(name=name,index=index,rejected=reason[:240]))
  else:raise AssertionError(('ineffective prefix control',name))
 return dict(independent_GPR_allocation_positive=positive,effective_controls=rejected)
def main():
 source.check_inputs()
 label='selected'
 data,refs=oracle.o.payload(p/'owner.o','func_151AD92C');raw=oracle.o.bound_blob(data,refs,oracle.SYMS)
 truth=list(struct.unpack('>464I',(p/'retail.bin').read_bytes()));candidate,edits=derive(raw)
 assert edits==source.PIN['home_edits']
 report=prove(truth,candidate);report.update(controls=controls(truth,candidate,edits),label=label,raw_sha256=hashlib.sha256(data).hexdigest(),home_edits=edits,source_installed=False,c_match_credit=0)
 with(p/'entry-symbolic-report.json').open('x')as stream:json.dump(report,stream,indent=2);stream.write('\n')
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
