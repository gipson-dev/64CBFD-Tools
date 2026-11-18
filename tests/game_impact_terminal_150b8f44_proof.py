"""Complete finite-value relation, with explicit FP-status exclusion.

This tests complete normal paths, mapped private bytes and public/provider values.
Independent finite FP calculations may reorder inside a quiet memory epoch; their
multiset and data dependencies must agree. FP control is stable between services,
but exception flags, traps, NaN payloads and fault-prefix identity are unclaimed.
No normalization, source installation or matching credit is produced here.
"""
from pathlib import Path
import collections,json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_impact_terminal_150b8f44_screen as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
e=g.e;ENTRY=source.ENTRY
TILE,QUERY,CLASSIFY,RNG,REAL,FACTORY,COPY,SPRAY,SOUND=0x150A3058,0x150AC9C0,0x15145C90,0x150ADA20,0x150ADA68,0x1513D594,0x10022EC0,0x15151670,0x10010F88

def canonical(off,raw):
 if raw:
  if -308<=off<0:return off-4
  if -312<=off<-308:return off+308
  if -316<=off<-312:return off-4
  if -320<=off<-316:return off+4
 return off

class State(g.State):
 def __init__(self,raw,remap=True):
  super().__init__('common');self.raw=raw;self.remap=raw and remap;self.frame_bytes=416
  self.mem={off:('PRIVATE_ENTRY',off)for off in range(-416,20)};self.exposed=set();self.accessed=set();self.fp_ops=[];self.control=('ENTRY_FP_CONTROL',)
  self.r[4:8]=[('ARG',i)for i in range(4)];self.store(('STACK',16),4,('ARG',4))
 def address(self,value):return('STACK',canonical(value[1],self.remap))if e.tagged(value,'STACK')else value
 def value(self,value):
  if e.tagged(value,'STACK'):return self.address(value)
  return tuple(self.value(v)for v in value)if isinstance(value,tuple)else value
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -416<=off and off+size<=20
   self.accessed.update(range(off,off+size));return g.join([self.mem[canonical(off+i,self.remap)]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -416<=off and off+size<=20
   self.accessed.update(range(off,off+size))
   for i in range(size):self.mem[canonical(off+i,self.remap)]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.value(self.mem[off])for off in range(-416,20))

class Program(g.Program):
 def __init__(self,words,terms,commute=True):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set();self.commute=commute
 def step(self,s,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt in(16,20)and not(fmt==16 and fn==6):
   assert(fmt==16 and fn in(0,1,2,3,5,7,13,60))or(fmt==20 and fn==32),('unsupported finite FP',hex(w))
   args=(s.f[fs],s.f[ft])if fmt==16 and fn in(0,1,2,3,60)else(s.f[fs],)
   if self.commute and fmt==16 and fn==2:args=tuple(sorted(args,key=repr))
   operation=(fmt,fn,args,s.control);s.fp_ops.append((s.epoch,operation));value=self.terms.term('FINITE_FP_VALUE',*operation)
   if fn==60:s.condition=value
   else:s.f[fd]=value
  elif op in(42,46):
   address=e.add(s.r[fmt],((w&65535)^32768)-32768);assert e.tagged(address,'STACK')
   off=address[1];k=off&3;assert(op==42 and k==0)or(op==46 and k==3),('unsupported partial copy alignment',off,op)
   s.store(('STACK',off&~3),4,s.r[ft])
  else:super().step(s,w)
  s.r[0]=0
 def call(self,s,target):
  n={TILE:4,QUERY:15,CLASSIFY:1,RNG:0,REAL:0,FACTORY:17,COPY:3,SPRAY:3,SOUND:10}[target];assert s.r[29]==('STACK',-416)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-400+4*i),4)for i in range(max(0,n-4)))
  if target==QUERY:args=(s.f[12],s.f[14],*args[2:])
  passed=tuple(s.address(v)for v in args);ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==QUERY:
   assert passed[7:]==(('STACK',-48),('STACK',-28),('STACK',-24),('STACK',-20),0,('STACK',-52),0,0)
   s.exposed.update((*range(-48,-30),*range(-28,-16),*range(-52,-48)))
  elif target==FACTORY:
   assert passed[0]==('STACK',-140)and passed[10]==('STACK',-48)
   observed=tuple(s.value(s.mem[i])for i in range(-140,-52));s.exposed.update(range(-140,-52))
  elif target==SPRAY:
   assert passed[0]==('STACK',-312);observed=tuple(s.value(s.mem[i])for i in range(-312,-148));s.exposed.update(range(-312,-148))
  elif target==COPY:
   assert passed[1:]==(('STACK',-148),8);e.plain(passed[0]);observed=tuple(s.value(s.mem[i])for i in range(-148,-140))
  s.trace.append(('CALL',target,passed,observed,s.control));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  if target==COPY:
   for i,value in enumerate(observed):s.trace.append(('COPY_WRITE',e.add(passed[0],i),value))
  for off in s.exposed:s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(max(4,n)):s.store(('STACK',-416+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=passed[0]if target==COPY else('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('FLOAT_RESULT',ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.control=('CALL_FP_CONTROL',ordinal);s.condition=('CALL_CONDITION',ordinal)

def compare(raw,retail,ordered=False,commute=True,remap=True):
 assert len(raw)==390 and len(retail)==391;terms=Terms();results=[];reports=[]
 for israw,words in((True,raw),(False,retail)):
  program=Program(words,terms,commute);answers={}
  for key,s in program.paths(0,{-4:'return'},State(israw,remap)).items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)and s.r[2]in(0,1)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   answers[key]=(s.trace,s.read_set,s.frame(),s.r[2],tuple(s.fp_ops)if ordered else collections.Counter(s.fp_ops),s.divisors)
  results.append(answers);reports.append(dict(raw=israw,paths=len(answers),visited=len(program.seen),unseen=[i for i in range(len(words))if 4*i not in program.seen]))
 assert results[0].keys()==results[1].keys(),('path keys differ',len(results[0]),len(results[1]))
 for key,a in results[0].items():
  b=results[1][key]
  if a!=b:
   part=next(i for i,(x,y)in enumerate(zip(a,b))if x!=y)
   if part==0:
    at=next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),None);raise AssertionError(('trace',at,repr(a[0][at]if at is not None else a[0])[:1600],repr(b[0][at]if at is not None else b[0])[:1600]))
   if part==2:
    at=next(i for i,(x,y)in enumerate(zip(a[2],b[2]))if x!=y);raise AssertionError(('private byte',at-416,a[2][at],b[2][at]))
   raise AssertionError(('observation',part,repr(a[part])[:1600],repr(b[part])[:1600]))
 return reports


def main(state=None,out=None):
 state=source.state()if state is None else state;out=source.OUT if out is None else out
 raw,retail=state['raw_words'],state['retail_words']
 assert{canonical(i,True)for i in range(-416,20)}==set(range(-416,20))
 reports=compare(raw,retail);assert reports==[dict(raw=True,paths=7,visited=389,unseen=[333]),dict(raw=False,paths=7,visited=390,unseen=[334])]
 controls=[]
 def reject(label,words,**options):
  try:compare(words,retail,**options)
  except(AssertionError,ValueError,KeyError)as error:
   reason=str(error);assert not any(v in reason.lower()for v in('unsupported','unbounded proof')),(label,reason)
   controls.append(dict(label=label,rejected=True,reason=reason[:200]));return
  raise AssertionError(('ineffective relation control',label))
 for label,word,mask in(('category',0x240a0004,1),('duration',0x2401001f,1),('copy-length',0x24060008,4),('high-volume',0x24057d00,1),('low-volume',0x3405fa00,1),('terminal-return',0x00001025,0x24021024)):
  assert raw.count(word)==1,(label,raw.count(word));bad=raw[:];bad[raw.index(word)]^=mask;reject(label,bad)
 for label,index in(('live-zero-delay',17),('unmapped-zero-coalescence',334)):
  bad=raw[:];assert bad[index]>>26==17 and bad[index]>>21&31==4;bad[index]=0;reject(label,bad)
 index=next(i for i,w in enumerate(raw)if w>>26==35 and w>>21&31==29 and w&65535==100)
 bad=raw[:];bad[index]=(bad[index]&0xffff0000)|96;reject('first-RNG-home',bad)
 bad=raw[:];w=bad[43];assert w>>26==17 and w&63==1;fs,ft=w>>11&31,w>>16&31;bad[43]=(w&~((31<<11)|(31<<16)))|(ft<<11)|(fs<<16);reject('subtraction-dependency',bad)
 reject('disabled-private-map',raw,remap=False)
 reject('strict-FP-order-boundary',raw,ordered=True)
 reject('strict-product-order-boundary',raw,commute=False)
 report=dict(passes=True,programs=reports,private_and_incoming_bytes=436,complete_seven_paths=True,all88_and164_descriptor_bytes=True,all18_metadata_and8_extra_bytes=True,public_provider_epochs=True,finite_FP_value_DAG_and_per_epoch_multiset=True,per_call_FP_control_retained=True,raw_FP_flags_traps_NaN_payloads_and_fault_identity_not_claimed=True,effective_negatives=controls,source_installed=False,c_match_credit=0)
 (out/'finite-relation-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='effective_negatives'}|{'effective_negatives':len(controls)}),flush=True);return report
