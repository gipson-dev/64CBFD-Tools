"""Complete finite-value/private relation with source-derived dead-spill histories.

All400 related bytes and eight untouched source-only gap bytes are accounted for.
Two unexposed retail spill words are related to actual source value histories;
this is not literal private-address or raw FP-status/fault-state identity.
"""
from pathlib import Path
import collections,json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_target_terminal_150b963c_fitting as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
e=g.e;ENTRY=source.ENTRY
RESOLVE,TRIG,RNG,REAL,QUERY,FACTORY,COPY,SPRAY,SOUND=0x15083e90,0x151423d8,0x150ada20,0x150ada68,0x15046c80,0x1513d594,0x10022ec0,0x15151a38,0x10010f88

def canonical(off,raw):
 if not raw:return off
 if -392<=off<-288:return off+8
 if -288<=off<-284:return off+16
 if -284<=off<-268:return off+268
 if -268<=off<-264:return off-8
 if -264<=off<-260:return off-16
 if -260<=off<-8:return off-8
 if -8<=off<0:return None
 return off

class State(g.State):
 def __init__(self,raw,frame,remap=True,ghosts=True):
  super().__init__('common');self.raw=raw;self.remap=raw and remap;self.use_ghosts=ghosts;self.frame_bytes=frame;assert frame==(392 if raw else 384)
  self.mem={off:('PRIVATE_ENTRY',off)for off in range(-384,16)};self.gap={off:('SOURCE_GAP_ENTRY',off)for off in range(-8,0)}
  self.exposed=set();self.accessed=set();self.fp_ops=[];self.control=('ENTRY_FP_CONTROL',);self.r[4]=('ARG',0);self.ghosts={off:None for off in(-8,-4)}
 def address(self,value):
  if e.tagged(value,'STACK'):
   mapped=canonical(value[1],self.remap);assert mapped is not None,('source gap address exposed',value);return('STACK',mapped)
  return value
 def value(self,value):
  if e.tagged(value,'STACK'):return self.address(value)
  return tuple(self.value(v)for v in value)if isinstance(value,tuple)else value
 def private_offset(self,off,size):
  assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=16
  self.accessed.update(range(off,off+size));mapped=[canonical(off+i,self.remap)for i in range(size)]
  assert None not in mapped,('source gap accessed',off,size)
  if self.raw:assert not any(-8<=n<0 for n in mapped),('source accessed value-only ghost home',off,size)
  return mapped
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):return g.join([self.mem[off]for off in self.private_offset(address[1],size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   for i,off in enumerate(self.private_offset(address[1],size)):self.mem[off]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):
  snapshot=dict(self.mem)
  if self.raw:
   assert all(self.mem[off]==('PRIVATE_ENTRY',off)for off in range(-8,0))
   assert self.gap=={off:('SOURCE_GAP_ENTRY',off)for off in range(-8,0)}
   for off,value in (self.ghosts.items()if self.use_ghosts else()):
    if value is None:continue
    for i in range(4):snapshot[off+i]=g.byte(value,8*(3-i))
  return tuple(self.value(snapshot[off])for off in range(-384,16))

class Program(g.Program):
 def instruction(self,pc):self.current_index=pc//4;return super().instruction(pc)
 def __init__(self,words,terms,commute_add=True,commute_mul=True,wrong_z=False,wrong_distance=False):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set();self.commute_add=commute_add;self.commute_mul=commute_mul;self.wrong_z=wrong_z;self.wrong_distance=wrong_distance
 def step(self,s,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt in(16,20)and not(fmt==16 and fn==6):
   assert(fmt==16 and fn in(0,1,2,3,13,60))or(fmt==20 and fn==32),('unsupported finite FP',hex(w))
   args=(s.f[fs],s.f[ft])if fmt==16 and fn in(0,1,2,3,60)else(s.f[fs],)
   if fmt==16 and((fn==0 and self.commute_add)or(fn==2 and self.commute_mul)):args=tuple(sorted(args,key=repr))
   operation=(fmt,fn,args,s.control);s.fp_ops.append((s.epoch,operation));value=self.terms.term('FINITE_FP_VALUE',*operation)
   if fn==60:s.condition=value
   else:s.f[fd]=value
  elif op in(42,46):
   at=e.add(s.r[fmt],((w&65535)^32768)-32768);assert e.tagged(at,'STACK');off=at[1];k=off&3;assert(op==42 and k==0)or(op==46 and k==3),('unsupported partial copy',off,op);s.store(('STACK',off&~3),4,s.r[ft])
  else:super().step(s,w)
  s.r[0]=0
  if s.raw and self.current_index==28:
   assert w==0xc470001c;s.ghosts[-8]=s.f[6 if self.wrong_z else 16]
  if s.raw and self.current_index==41:
   assert w==0x460a4480;s.ghosts[-4]=s.f[0 if self.wrong_distance else 18]
 def call(self,s,target):
  n={RESOLVE:1,TRIG:1,RNG:0,REAL:0,QUERY:4,FACTORY:17,COPY:3,SPRAY:3,SOUND:10}[target];assert s.r[29]==('STACK',-s.frame_bytes)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-s.frame_bytes+16+4*i),4)for i in range(max(0,n-4)));passed=tuple(s.address(v)for v in args);ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==QUERY:assert passed[0]==('STACK',-36);s.exposed.update(range(-36,-24))
  elif target==FACTORY:
   assert passed[0]==('STACK',-124);observed=tuple(s.value(s.mem[i])for i in range(-124,-36));s.exposed.update(range(-124,-36))
  elif target==SPRAY:
   assert passed[0]==('STACK',-268);observed=tuple(s.value(s.mem[i])for i in range(-268,-132));s.exposed.update(range(-268,-132))
  elif target==COPY:
   assert passed[1:]==(('STACK',-132),8);e.plain(passed[0]);observed=tuple(s.value(s.mem[i])for i in range(-132,-124))
  s.trace.append(('CALL',target,passed,observed,s.control));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  if target==COPY:
   for i,v in enumerate(observed):s.trace.append(('COPY_WRITE',e.add(passed[0],i),v))
  for off in s.exposed:s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(max(4,n)):s.store(('STACK',-s.frame_bytes+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=passed[0]if target==COPY else('RESULT',target,ordinal)
  if target in(REAL,TRIG):s.f[0]=('FLOAT_RESULT',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.control=('CALL_FP_CONTROL',ordinal);s.condition=('CALL_CONDITION',ordinal)

def compare(raw,retail,ordered=False,remap=True,ghosts=True,**options):
 assert(len(raw),len(retail))==(434,438)
 terms=Terms();results=[];reports=[]
 def expand(value,depth=6):
  if not depth:return value
  if isinstance(value,tuple)and value and value[0]=='EXPRESSION':
   reverse={v:k for k,v in terms.values.items()};return expand(reverse[value],depth-1)
  return tuple(expand(v,depth)for v in value)if isinstance(value,tuple)else value
 for israw,words in((True,raw),(False,retail)):
  program=Program(words,terms,**options);answers={}
  for key,s in program.paths(0,{-4:'return'},State(israw,65536-(words[0]&65535),remap,ghosts)).items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)and s.r[2]in(0,1)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   answers[key]=(s.trace,s.read_set,s.r[2],tuple(s.fp_ops)if ordered else collections.Counter(s.fp_ops),s.divisors,s.frame())
  results.append(answers);reports.append(dict(raw=israw,paths=len(answers),visited=len(program.seen),unseen=[i for i in range(len(words))if 4*i not in program.seen]))
 assert results[0].keys()==results[1].keys(),('path keys differ',len(results[0]),len(results[1]),repr(next(iter(results[0].keys()-results[1].keys()),None))[:400],repr(next(iter(results[1].keys()-results[0].keys()),None))[:400])
 for key,a in results[0].items():
  b=results[1][key]
  if a!=b:
   part=next(i for i,(x,y)in enumerate(zip(a,b))if x!=y)
   if part==0:
    at=next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),None);raise AssertionError(('trace',at,repr(expand(a[0][at]if at is not None else a[0]))[:1800],repr(expand(b[0][at]if at is not None else b[0]))[:1800],repr(a[1]-b[1])[:700],repr(b[1]-a[1])[:700]))
   raise AssertionError(('observation',part,repr(a[part])[:1800],repr(b[part])[:1800]))
 return reports

def main(state=None,out=None):
 state=source.state()if state is None else state;out=source.OUT if out is None else out;raw,retail=state['raw_words'],state['retail_words']
 mapped=[canonical(i,True)for i in range(-392,16)if canonical(i,True)is not None]
 assert len(mapped)==len(set(mapped))==400 and set(mapped)==set(range(-384,16))
 reports=compare(raw,retail);assert reports==[dict(raw=True,paths=77,visited=434,unseen=[]),dict(raw=False,paths=77,visited=438,unseen=[])]
 controls=[]
 def reject(label,words,**options):
  try:compare(words,retail,**options)
  except(AssertionError,ValueError,KeyError)as error:
   reason=str(error);assert not any(v in reason.lower()for v in('unsupported','unbounded proof')),(label,reason)
   controls.append(dict(label=label,rejected=True,reason=reason[:220]));return
  raise AssertionError(('ineffective relation control',label))
 for label,word,mask in(('duration',0x2401001f,1),('copy-length',0x24060008,4),('sound-volume',0x240561a8,1),('bounce-timer',0x2419012c,1),('query-height',0x3c0144fa,1)):
  assert raw.count(word)==1,(label,raw.count(word));bad=raw[:];bad[raw.index(word)]^=mask;reject(label,bad)
 bad=raw[:];assert bad[11]==0x906f003b;bad[11]^=1;reject('target-tag-byte',bad)
 index=max(i for i,w in enumerate(raw)if w==0x3c014248);bad=raw[:];bad[index]^=1;reject('destination-height',bad)
 index=next(int(at)//4 for at,bindings in source.PIN['refs'].items()if ['R_MIPS_LO16','D_8009FE00']in bindings);bad=raw[:];assert bad[index]>>26==49;bad[index]^=4;reject('steering-factor-address',bad)
 bad=raw[:];assert bad[7]==0;bad[7]=0x8fa80180;reject('source-only-gap-access',bad)
 reject('disabled-private-projection',raw,remap=False)
 reject('disabled-spill-history',raw,ghosts=False)
 reject('wrong-Z-spill-history',raw,wrong_z=True)
 reject('wrong-distance-spill-history',raw,wrong_distance=True)
 reject('strict-addition-order-boundary',raw,commute_add=False)
 reject('strict-product-order-boundary',raw,commute_mul=False)
 reject('strict-FP-order-boundary',raw,ordered=True)
 report=dict(passes=True,programs=reports,complete_paths=77,related_private_and_incoming_bytes=400,source_private_and_incoming_bytes=408,untouched_source_gap_bytes=8,value_history_related_retail_words=2,source_backing_bytes_unchanged=True,all88_and136_descriptor_bytes=True,all8_extra_bytes=True,finite_addition_and_product_commutativity=True,per_epoch_FP_multiset_and_data_dependencies=True,raw_FP_flags_traps_NaN_payloads_async_and_fault_identity_not_claimed=True,effective_negatives=controls,source_installed=False,c_match_credit=0)
 (out/'finite-private-relation-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='effective_negatives'}|{'effective_negatives':len(controls)}),flush=True);return report
