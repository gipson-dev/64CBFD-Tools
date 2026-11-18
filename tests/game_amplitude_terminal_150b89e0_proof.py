"""Complete normal-domain instruction relation for the amplitude terminal callback.

All public/FP observations remain ordered. The single reversed multiply has an
explicit finite-arithmetic value relation; raw NaN-payload identity is unclaimed.
The extra raw frame gap must never be accessed. Providers may retain exposed
descriptor/matrix bytes, not unpassed locals or implementation PCs. No fault or
hardware FP acceptance is inferred from this symbolic normal-execution model.
"""
from pathlib import Path
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_amplitude_terminal_150b89e0_screen as source
e=g.e;ENTRY=source.ENTRY
RNG,REAL,FACTORY,SPRAY,SOUND,MATRIX,TRANSFORM,COPY=0x150ADA20,0x150ADA68,0x1513D594,0x15151A38,0x10010F88,0x150A8050,0x150A7960,0x10022EC0

def canonical(off,raw):
 if raw:
  if -320<=off<-312:raise AssertionError(('source-only gap accessed',off))
  if -408<=off<-320:return off+8
  if -308<=off<-304:return off+8
  if -300<=off<-296:return off-8
 return off

class State(g.State):
 def __init__(self,raw,remap=True):
  super().__init__('common');self.raw=raw;self.remap=raw and remap;self.frame_bytes=408 if raw else 400
  self.mem={off:('PRIVATE_ENTRY',off)for off in range(-400,24)};self.exposed=set();self.accessed=set();self.products=[]
  self.r[4:8]=[('ARG',i)for i in range(4)]
  for i in(4,5):self.store(('STACK',4*i),4,('ARG',i))
 def address(self,value):return('STACK',canonical(value[1],self.remap))if e.tagged(value,'STACK')else value
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=24
   self.accessed.update(range(off,off+size));return g.join([self.mem[canonical(off+i,self.remap)]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=24
   self.accessed.update(range(off,off+size))
   for i in range(size):self.mem[canonical(off+i,self.remap)]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def value(self,value):
  if e.tagged(value,'STACK'):return self.address(value)
  return tuple(self.value(v)for v in value)if isinstance(value,tuple)else value
 def frame(self):return tuple(self.value(self.mem[off])for off in range(-400,24))

class Program(g.Program):
 def __init__(self,words,terms,commute):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set();self.commute=commute;self.last_pc=None
 def instruction(self,pc):self.last_pc=pc;return super().instruction(pc)
 def step(self,s,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn==7:
   observation=(fmt,fn,(s.f[fs],),s.fcsr);s.trace.append(('FP',observation));s.f[fd]=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
  elif self.commute and self.last_pc==266*4:
   assert w in(0x460A0402,0x46005402)and op==17 and fmt==16 and fn==2
   args=(s.f[fs],s.f[ft]);ordered=tuple(sorted(args,key=repr));s.products.append((args,ordered));observation=(fmt,fn,ordered,s.fcsr)
   s.trace.append(('FINITE_COMMUTATIVE_FP_MUL',observation));s.f[fd]=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
  else:super().step(s,w)
  s.r[0]=0
 def call(self,s,target):
  n={RNG:0,REAL:0,FACTORY:17,SPRAY:3,SOUND:10,MATRIX:4,TRANSFORM:7,COPY:3}[target];assert s.r[29]==('STACK',-s.frame_bytes)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-s.frame_bytes+16+4*i),4)for i in range(max(0,n-4)))
  passed=tuple(s.address(a)for a in args);ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==FACTORY:
   assert passed[0]==('STACK',-88)and passed[2:5]==(24,0,0)and passed[7:10]==(0x43fa0000,0x43fa0000,0)
   observed=tuple(s.mem[i]for i in range(-88,0));s.exposed.update(range(-88,0))
  elif target==SPRAY:
   assert passed[0]==('STACK',-232);observed=tuple(s.mem[i]for i in range(-232,-96));s.exposed.update(range(-232,-96))
  elif target==MATRIX:
   assert passed[0]==('STACK',-296);s.exposed.update(range(-296,-232))
  elif target==TRANSFORM:
   assert passed[:4]==(('STACK',-296),0,0,0x43480000);observed=tuple(s.mem[i]for i in range(-296,-232))
  elif target==COPY:
   assert passed[1:]==(('STACK',-96),8);e.plain(passed[0]);observed=tuple(s.mem[i]for i in range(-96,-88))
  s.trace.append(('CALL',target,passed,observed,s.fcsr));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  if target==COPY:
   for i,value in enumerate(observed):s.trace.append(('COPY_WRITE',e.add(passed[0],i),value))
  for off in s.exposed:s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(max(4,n)):s.store(('STACK',-s.frame_bytes+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=passed[0]if target==COPY else('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('FLOAT_RESULT',ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)

def compare(raw,retail,commute=True,remap=True):
 assert len(raw)==len(retail)==345;terms=Terms();results=[];coverage=[];max_steps=[]
 for side,words in enumerate((raw,retail)):
  p=Program(words,terms,commute);answers={};steps=[]
  for key,s in p.paths(0,{-4:'return'},State(side==0,remap)).items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)and s.r[2]in(0,1)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   if side==0:assert not set(range(-320,-312))&s.accessed
   answers[key]=(s.trace,s.read_set,s.frame(),s.r[2],s.fcsr,s.divisors);steps.append(s.steps)
  assert p.seen==set(range(0,1380,4))-{259*4},('instruction coverage',len(p.seen));results.append(answers);coverage.append(len(p.seen));max_steps.append(max(steps))
 assert results[0].keys()==results[1].keys(),('path predicates',len(results[0]),len(results[1]))
 for key,a in results[0].items():
  b=results[1][key]
  if a!=b:
   part=next(i for i,(x,y)in enumerate(zip(a,b))if x!=y)
   if part==0:
    at=next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),None);raise AssertionError(('transfer trace',at,repr(a[0][at]if at is not None else a[0])[:2200],repr(b[0][at]if at is not None else b[0])[:2200]))
   if part==2:
    at=next(i for i,(x,y)in enumerate(zip(a[part],b[part]))if x!=y);raise AssertionError(('private byte',at-400,a[part][at],b[part][at]))
   raise AssertionError(('transfer part',part,repr(a[part])[:2000],repr(b[part])[:2000]))
 return dict(paths=len(results[0]),coverage=coverage,max_steps=max_steps)

def main(state=None):
 state=source.state()if state is None else state;raw,retail=state['raw_words'],state['retail_words'];assert raw[259]==retail[259]==0xC6000014
 assert {canonical(i,True)for i in range(-408,24)if not -320<=i<-312}==set(range(-400,24))
 result=compare(raw,retail);controls=[]
 tests=[('category',retail,retail.index(0x24180004),1),('duration-divisor',retail,retail.index(0x2401001f),1),('extra-copy-length',retail,retail.index(0x24060008),4),('low-flags-mask',retail,retail.index(0x2401ff00),1),('terminal-return',retail,retail.index(0x00001025),0x24021024)]
 for label,base,index,mask in tests:
  bad=base[:];bad[index]^=mask
  try:compare(raw,bad)
  except(AssertionError,ValueError,KeyError)as error:
   assert 'unsupported'not in str(error).lower(),(label,error);controls.append(label)
  else:raise AssertionError(('ineffective relation control',label,index))
 index=next(i for i,w in enumerate(raw)if w>>26==35 and w>>21&31==29 and w&65535==108)
 for label,off in(('first-RNG-home',104),('source-gap-access',92)):
  bad=raw[:];bad[index]=(bad[index]&0xffff0000)|off
  try:compare(bad,retail)
  except(AssertionError,ValueError,KeyError)as error:
   assert 'unsupported'not in str(error).lower(),(label,error);controls.append(label)
  else:raise AssertionError(('ineffective relation control',label))
 bad=raw[:];bad[12],bad[14]=bad[14],bad[12]
 try:compare(bad,retail)
 except AssertionError as error:assert 'unsupported'not in str(error).lower();controls.append('ordered-opening-FP')
 else:raise AssertionError('ineffective FP-order control')
 try:compare(raw,retail,commute=False)
 except AssertionError as error:
  assert isinstance(error.args[0],tuple)and error.args[0][0]=='transfer trace',error;controls.append('strict-raw-product-order')
 else:raise AssertionError('raw product-order boundary disappeared')
 report=dict(passes=True,**result,private_incoming_bytes=424,source_only_gap_bytes=8,source_gap_accesses=0,full88_and136_descriptor_bytes=True,full8_extra_bytes=True,all64_matrix_bytes=True,arbitrary_public_provider_epochs=True,ordered_FP_FCSR_except_one_finite_commutative_product=True,finite_arithmetic_and_defined_conversion_domain=True,raw_NaN_payload_or_fault_identity_not_claimed=True,effective_negatives=controls,source_installed=False,c_match_credit=0)
 (source.OUT/'relation-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
