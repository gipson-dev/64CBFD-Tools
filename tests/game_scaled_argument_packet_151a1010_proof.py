"""Independent symbolic normal-execution check for the private scaled packet.

Mapped private stacks and immutable literals. Compares the complete typed call,
ordered FP instructions and FCSR transitions, then saved-register/return custody.
The provider cannot inspect code/return PCs or unpassed private frame bytes.
Different private frame sizes are explicitly allowed here, not matching credit.
No hardware, fault-prefix, portable undefined-input or runtime reachability claim.
"""
from pathlib import Path
import hashlib,importlib.util,json,struct,sys
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_side_ring_renderer_1519fe6c_coverage import static
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_scaled_argument_packet_151a1010_recovery as m
p,r,ENTRY,CALLEE,CONST=m.OUT,m.ROOT,m.ENTRY,m.CALLEE,m.CONST

def short(value):
 """Exact low-16 linear reduction followed by signed 16-to-32 extension."""
 def collect(v,k,terms):
  if e.tagged(v,'SIGN16'):v=v[1]
  if isinstance(v,int):return v*k
  if e.tagged(v,'LINEAR'):
   const=v[1]*k
   for term,n in v[2]:const+=collect(term,n*k,terms)
   return const
  terms[v]=(terms.get(v,0)+k)&65535;return 0
 terms={};const=collect(value,1,terms)&65535;form=e.affine(const,{v:k for v,k in terms.items()if k})
 if isinstance(form,int):return (((form&65535)^32768)-32768)&e.U32
 return ('SIGN16',form)

class State(e.State):
 def __init__(self,side,provider):
  super().__init__('common','scaled');self.side=side;self.provider=provider;self.mem={};self.private_writes=[];self.fcsr=('ENTRY_FCSR',)
  self.r=[('UNDEFINED_GPR',side,i)for i in range(32)];self.r[0]=0;self.r[29]=('STACK',0);self.r[31]=('RETURN',)
  self.f=[('UNDEFINED_FPR',side,i)for i in range(32)]
  for i in(*range(16,24),28,30):self.r[i]=('ENTRY',i)
  for i in range(20,32):self.f[i]=('ENTRY_FP',i)
  self.f[12],self.f[14]=('X',),('Y',);self.r[6],self.r[7]=('VALUE',),('SPAN_WORD',)
  for i in range(8):self.mem[4*i]=('ENTRY_HOME',i)
  for i,v in enumerate((('SCALE',),('RATE',),('VARIANT_WORD',),('FLAGS',)),4):self.mem[4*i]=v
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,4)and(size==1 or off%4==0)
   value=self.mem.get(off&~3,('PRIVATE_ENTRY',off&~3))
   if size==1:assert off%4==3;return e.bitop('AND',value,255)
   return value
  assert address==CONST and size==4,('unexpected public read',address,size)
  return 0x44BB8000
 def store(self,address,size,value):
  assert e.tagged(address,'STACK')and size==4 and address[1]%4==0,('unexpected write',address,size)
  e.plain(value);self.mem[address[1]]=value;self.private_writes.append((address[1],size))

class Program(opening.Program):
 def __init__(self,words,terms,provider):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.provider=provider;self.seen=set();self.frame=(-words[0])&65535
 def instruction(self,pc):self.seen.add(pc);return super().instruction(pc)
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==0 and fn==0 and(w>>6&31)==16:s.r[w>>11&31]=('LEFT16',short(s.r[w>>16&31]))
  elif op==0 and fn==3 and(w>>6&31)==16:
   value=s.r[w>>16&31];assert e.tagged(value,'LEFT16'),('unsupported shift pair',value);s.r[w>>11&31]=value[1]
  elif op==17 and fmt==4:s.f[w>>11&31]=s.r[w>>16&31]
  elif op==17 and fmt==16:
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31
   if fn==6:s.f[fd]=s.f[fs]
   else:
    assert fn in(2,13),('unsupported scaled FP',hex(w))
    args=(s.f[fs],s.f[ft])if fn==2 else(s.f[fs],)
    assert not any(e.has_tag(v,'UNDEFINED_FPR')for v in args),('undefined FP input',args)
    observation=(fn,args,s.fcsr);s.trace.append(('FP',observation));s.f[fd]=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
  else:super().step(s,w)
 def call(self,s,target):
  assert target==CALLEE and s.r[29]==('STACK',-self.frame)
  args=(s.f[12],s.f[14],s.r[6],s.r[7],*tuple(s.load(('STACK',-self.frame+4*i),4,b'')for i in range(4,28)))
  assert not any(e.has_tag(v,'UNDEFINED_GPR')or e.has_tag(v,'UNDEFINED_FPR')for v in args)
  s.trace.append(('CALL',target,args,s.fcsr));s.calls[target]+=1
  if self.provider=='retail-stub':
   for w in STUB[:4]:self.step(s,w)
  else:
   assert self.provider=='opaque-o32'
   for i in range(28):s.store(('STACK',-self.frame+4*i),4,('CALL_HOME',i))
   for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',i)
   for i in range(20):s.f[i]=('CALLER_FP',i)
   s.fcsr=('PROVIDER_FCSR',);s.hi=('PROVIDER_HI',);s.lo=('PROVIDER_LO',)

def observable(s,frame):
 assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('return custody',s.r[29],s.r[31])
 assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],'saved ABI'
 assert s.calls=={CALLEE:1};assert s.mem[8]==('VALUE',)and s.mem[12]==('SPAN_WORD',)
 for off,size in s.private_writes:assert -frame<=off and off+size<=0 or off in(8,12),('private write escape',off,size)
 assert s.mem[0]==('ENTRY_HOME',0)and s.mem[4]==('ENTRY_HOME',1)
 assert all(s.mem[4*i]==v for i,v in enumerate((('SCALE',),('RATE',),('VARIANT_WORD',),('FLAGS',)),4))
 return tuple(s.trace),s.fcsr,tuple(s.f[20:])

STUB=[0xe7ac0000,0xe7ae0004,0xafa60008,0xafa7000c,0x03e00008,0]
def prove(raw,retail):
 results={};coverage={}
 for provider in('retail-stub','opaque-o32'):
  terms=Terms();pairs={}
  for side,words in(('raw',raw),('retail',retail)):
   program=Program(words,terms,provider);paths=program.paths(0,{-4:'return'},State(side,provider));pairs[side]={key:observable(state,program.frame)for key,state in paths.items()};assert program.seen==static(words),('incomplete CFG',side,static(words)-program.seen);coverage[side]=len(program.seen)
  assert pairs['raw'].keys()==pairs['retail'].keys(),('path predicates',list(pairs['raw']),list(pairs['retail']))
  for key in pairs['raw']:
   assert pairs['raw'][key]==pairs['retail'][key],('ordered transfer mismatch',provider,key,repr(pairs['raw'][key])[:1800],repr(pairs['retail'][key])[:1800])
  results[provider]=len(pairs['raw'])
 return dict(paths_by_provider=results,reachable_words=coverage,all28_call_arguments=True,ordered_FP_and_FCSR=True,original_caller_homes_preserved=True,saved_ABI_and_return_custody=True,raw_frame=(-raw[0])&65535,retail_frame=(-retail[0])&65535,private_frame_identity=False,c_match_credit=0)

def main():
 record=json.loads((p/'production-baseline/fingerprints.json').read_text())
 def immutable():
  for name,h in record['inputs'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==h,name
 immutable();raw,refs=payload(p/'inline-updateformal.o','func_151A1010');words=bound_blob(raw,refs,{'D_800A8D28':CONST,'func_151A11CC':CALLEE});image=(r/'conker/conker.us.bin').read_bytes();retail=list(struct.unpack_from('>111I',image,0x1CE4C0));assert list(struct.unpack_from('>6I',image,0x1CE67C))==STUB
 report=prove(words,retail);controls=[]
 # Independent saved-register rename is accepted without a schedule template.
 alternative=words[:]
 for i,w in enumerate(alternative):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==0:shifts=(21,)if fn==8 else(16,11)if fn in(0,2,3)else(21,16,11)
  elif op==17:shifts=(16,)if fmt in(0,4)else()
  elif op==3:shifts=()
  elif op in(6,7,49,57):shifts=(21,)
  elif op==15:shifts=(16,)
  else:assert op in(9,35,36,43);shifts=(21,16)
  for shift in shifts:
   reg=w>>shift&31
   if reg in(16,17):w=(w&~(31<<shift))|((33-reg)<<shift)
  alternative[i]=w
 assert alternative!=words and prove(alternative,retail)==report
 for label,index,change in (
  ('span-subtraction',next(i for i,w in enumerate(words)if w>>26==9 and w&65535==65504),lambda w:w+1),
  ('clamp-one',next(i for i,w in enumerate(words)if w>>26==9 and w>>21&31==0 and w&65535==1),lambda w:w+1),
  ('FP-operand-order',next(i for i,w in enumerate(words)if w>>26==17 and w&63==2),lambda w:(w&~((31<<11)|(31<<16)))|((w>>11&31)<<16)|((w>>16&31)<<11)),
  ('saved-return-home',next(i for i,w in enumerate(words)if w>>26==43 and w>>16&31==31),lambda w:w-4),
  ('variant-signedness',next(i for i,w in enumerate(words)if w>>26==36),lambda w:(w&0x03ffffff)|(32<<26)),
  ('unclamped-plus16',next(i for i,w in enumerate(words)if w>>26==9 and w>>21&31!=0 and w&65535==16),lambda w:w+1),
 ):
  bad=words[:];bad[index]=change(bad[index]);assert bad!=words
  try:prove(bad,retail)
  except AssertionError as error:
   reason=str(error);assert not any(v in reason for v in('unsupported','unbounded proof','escaped code')),('invalid control',label,reason);controls.append(dict(name=label,rejected=reason[:200]))
  else:raise AssertionError(('ineffective control',label))
 report['independent_saved_register_rename_positive']=True;report['effective_corruptions']=controls;report['raw_sha256']=hashlib.sha256(raw).hexdigest();report['production_inputs_unchanged']=len(record['inputs']);immutable();(p/'whole-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
