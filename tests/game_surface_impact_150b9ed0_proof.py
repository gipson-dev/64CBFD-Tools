"""Instruction-driven whole-path relation, with a complete private-byte projection.

All348 source frame/incoming bytes map injectively to the364-byte retail state.
Sixteen retail-only bytes are untouched and unexposed throughout. This is a
related-state proof, not literal physical stack identity or a hardware/fault claim.
"""
from pathlib import Path
import collections,json
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_surface_impact_150b9ed0_screen as source

e=g.e;ENTRY=source.ENTRY
GATE,QUERY,PREDICATE,RNG,REAL,FACTORY,SPRAY=0x150a3058,0x150ac9c0,0x15145c90,0x150ada20,0x150ada68,0x1513c650,0x151511fc
EXTRA=range(-16,0)
_source_unused=list(range(-248,-220))+list(range(-216,-212))
_retail_unused=list(range(-264,-252))+list(range(-244,-240))+list(range(-236,-232))+list(range(-28,-16))
assert len(_source_unused)==len(_retail_unused)==32
UNUSED=dict(zip(_source_unused,_retail_unused))

def canonical(off,raw):
 if not raw:return off
 if -328<=off<-248:return off-16
 if off in UNUSED:return UNUSED[off]
 if -220<=off<-216:return off-20
 if -212<=off<-208:return off-36
 if -208<=off<-204:return off-44
 if -204<=off<-12:return off-28
 if -12<=off<-8:return off-20
 if -8<=off<-4:return off-28
 if -4<=off<0:return off-36
 assert 0<=off<20,off
 return off

def negate_word(value):
 if isinstance(value,int):return value^0x80000000
 if e.tagged(value,'FP_NEGATE'):return value[1]
 return('FP_NEGATE',value)

class State(g.State):
 def __init__(self,raw,remap=True):
  super().__init__('common');self.raw=raw;self.remap=raw and remap;self.frame_bytes=328 if raw else 344
  self.mem={off:('PRIVATE_ENTRY',off)for off in range(-344,20)}
  self.exposed=set();self.accessed=set();self.fp_ops=[];self.control=('ENTRY_FP_CONTROL',)
  self.r[4:8]=[('ARG',i)for i in range(4)]
  for i in range(4):self.mem[16+i]=g.byte(('ARG',4),8*(3-i))
 def address(self,value):
  return('STACK',canonical(value[1],self.remap))if e.tagged(value,'STACK')else value
 def value(self,value):
  if e.tagged(value,'STACK'):return self.address(value)
  return tuple(self.value(v)for v in value)if isinstance(value,tuple)else value
 def private(self,off,size):
  assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=20,('private bounds',off,size)
  self.accessed.update(range(off,off+size));return[canonical(off+i,self.remap)for i in range(size)]
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):return g.join([self.mem[off]for off in self.private(address[1],size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   for i,off in enumerate(self.private(address[1],size)):self.mem[off]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):
  assert all(self.mem[i]==('PRIVATE_ENTRY',i)for i in EXTRA),('retail-only byte changed',self.raw)
  if not self.raw:assert not(set(EXTRA)&self.accessed),('retail-only byte accessed',self.accessed&set(EXTRA))
  assert not(set(EXTRA)&self.exposed)
  return tuple(self.value(self.mem[i])for i in range(-344,20))

class Program(g.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def step(self,s,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==0 and fn==39:
   assert ft==0,('unsupported NOR operands',hex(w));s.r[fs]=e.add(e.scale(s.r[fmt],-1),e.U32)
  elif op==17 and fmt in(16,20)and not(fmt==16 and fn==6):
   assert(fmt==16 and fn in(0,1,2,7,13))or(fmt==20 and fn==32),('unsupported finite FP',hex(w))
   args=(s.f[fs],s.f[ft])if fmt==16 and fn in(0,1,2)else(s.f[fs],)
   operation=(fmt,fn,args,s.control);s.fp_ops.append((s.epoch,operation))
   s.f[fd]=negate_word(args[0])if fmt==16 and fn==7 else self.terms.term('FINITE_FP_VALUE',*operation)
   if fmt==16 and fn==13:s.divisors.add(('VALID_SIGNED32_TRUNCATION',args[0]))
  elif op in(42,46):
   at=e.add(s.r[fmt],((w&65535)^32768)-32768);assert e.tagged(at,'STACK');off=at[1]
   assert(op==42 and off%4==0)or(op==46 and off%4==3),('unsupported partial copy',off,op)
   s.store(('STACK',off&~3),4,s.r[ft])
  else:super().step(s,w)
  s.r[0]=0
 def call(self,s,target):
  n={GATE:4,QUERY:15,PREDICATE:1,RNG:0,REAL:0,FACTORY:16,SPRAY:3}[target]
  assert s.r[29]==('STACK',-s.frame_bytes)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-s.frame_bytes+16+4*i),4)for i in range(max(0,n-4)))
  if target==QUERY:args=(s.f[12],s.f[14],*args[2:])
  passed=tuple(s.address(v)for v in args);ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==QUERY:
   assert passed[7:]==(('STACK',-72),('STACK',-52),('STACK',-48),('STACK',-44),0,('STACK',-76),0,0),('query roles',passed)
   s.exposed.update(range(-76,-54));s.exposed.update(range(-52,-40))
  elif target==FACTORY:
   assert passed[0]==('STACK',-116)and passed[3]==('STACK',-72),('factory roles',passed)
   observed=tuple(s.value(s.mem[i])for i in range(-116,-76));s.exposed.update(range(-116,-76))
  elif target==SPRAY:
   assert passed[0]==('STACK',-232),('spray roles',passed)
   observed=tuple(s.value(s.mem[i])for i in range(-232,-116));s.exposed.update(range(-232,-116))
  s.trace.append(('CALL',target,passed,observed,s.control));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  for off in s.exposed:s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(max(4,n)):s.store(('STACK',-s.frame_bytes+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('FLOAT_RESULT',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.control=('CALL_FP_CONTROL',ordinal);s.condition=('CALL_CONDITION',ordinal)

def compare(raw,retail,remap=True,ordered=True):
 assert len(raw)==len(retail)==291
 mapped=[canonical(i,True)for i in range(-328,20)]
 assert len(mapped)==len(set(mapped))==348 and set(mapped)==set(range(-344,20))-set(EXTRA)
 terms=Terms();results=[];reports=[]
 for israw,words in((True,raw),(False,retail)):
  program=Program(words,terms);answers={}
  for key,s in program.paths(0,{-4:'return'},State(israw,remap)).items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   answers[key]=(s.trace,s.read_set,tuple(s.fp_ops)if ordered else collections.Counter(s.fp_ops),s.divisors,s.frame())
  results.append(answers);reports.append(dict(raw=israw,paths=len(answers),visited=len(program.seen),unseen=[i for i in range(291)if 4*i not in program.seen]))
 assert results[0].keys()==results[1].keys(),('path keys differ',len(results[0]),len(results[1]))
 for key,a in results[0].items():
  b=results[1][key]
  if a!=b:
   part=next(i for i,(x,y)in enumerate(zip(a,b))if x!=y)
   if part==0:
    at=next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),None)
    raise AssertionError(('trace',at,repr(a[0][at]if at is not None else a[0])[:2200],repr(b[0][at]if at is not None else b[0])[:2200]))
   raise AssertionError(('observation',part,repr(a[part])[:2200],repr(b[part])[:2200]))
 return reports

def main(state,out):
 raw,retail=state['raw_words'],state['retail_words'];reports=compare(raw,retail)
 assert reports==[dict(raw=True,paths=11,visited=291,unseen=[]),dict(raw=False,paths=11,visited=291,unseen=[])]
 controls=[]
 def reject(label,a,b=retail,**options):
  try:compare(a,b,**options)
  except(AssertionError,ValueError,KeyError)as error:
   reason=str(error);assert not any(v in reason.lower()for v in('unsupported','unbounded proof')),(label,reason)
   controls.append(dict(label=label,rejected=True,reason=reason[:250]));return
  raise AssertionError(('ineffective relation control',label))
 for label,old,new in(('gate-subtype',0x24040002,0x24040003),('duration',0x24010033,0x24010032),('color',0x24010065,0x24010064)):
  assert raw.count(old)==1;bad=raw[:];bad[raw.index(old)]=new;reject(label,bad)
 for label,old,new in(('integrity-sum',0x3421095e,0x3421095f),('integrity-failure-byte',0xa0384060,0xa0384061),('query-vertical-delta',0x44809000,0x44819000),('spray-negative-zero',0x46005107,0x46005106),('random-byte-mask',0x320f00ff,0x320f00fe),('mode-home',0x93ad0157,0x93ad0156),('tag-home',0x8fae0158,0x8fae0154),('query-branch-polarity',0x504000bc,0x544000bc)):
  assert raw.count(old)==1,(label,raw.count(old));bad=raw[:];bad[raw.index(old)]=new;reject(label,bad)
 index=next(int(at)//4 for at,bindings in source.PIN['refs'].items()if ['R_MIPS_LO16','D_8009FE10']in bindings)
 bad=raw[:];assert bad[index]>>26==49;bad[index]^=4;reject('late-constant-address',bad)
 bad=raw[:];assert bad[-1]==0;bad[-1]=0xafa0ff20;reject('unexposed-source-private-write',bad)
 bad=retail[:];assert bad[-1]==0;bad[-1]=0xafa0fff4;reject('retail-only-byte-write',raw,bad)
 reject('disabled-private-projection',raw,remap=False)
 report=dict(passes=True,programs=reports,complete_paths=11,source_private_and_incoming_bytes=348,retail_private_and_incoming_bytes=364,retail_only_untouched_unexposed_bytes=16,full_related_frame_at_every_call_and_return=True,all40_and116_descriptor_bytes=True,all_18_query_context_bytes=True,ordered_FP_operations_and_operands=True,per_call_FP_control=True,arbitrary_public_aliases_with_quiet_read_epochs=True,source_private_identity_not_claimed=True,raw_FP_flags_traps_NaN_payloads_async_and_fault_identity_not_claimed=True,effective_negatives=controls,source_installed=False,c_match_credit=0)
 out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'private-relation-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='effective_negatives'}|{'effective_negatives':len(controls)}),flush=True);return report
