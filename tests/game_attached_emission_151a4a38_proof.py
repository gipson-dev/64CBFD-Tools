"""Ordered full callback relation with original public aliases and private homes."""
from pathlib import Path
import hashlib,json,struct,sys
from tools.tests import game_growth_curve_151a1fb4_proof as base
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_attached_emission_151a4a38_recovery as source
O=source.OUT;R=source.ROOT;ENTRY=source.ENTRY;RNG=0x150ADA20;TRANSFORM=0x15143134;EMIT=0x15153634;e=base.e
class State(base.State):
 def __init__(self,side):
  super().__init__(side);self.r[4]=('OWNER',);self.mem={off:('PRIVATE_BYTE',off)for off in range(-168,16)};self.exposed_output=False;self.exposed_packet=False
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert off%size==0 and -168<=off and off+size<=16,('private read escape',off,size)
   return base.join([self.mem[off+i]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert off%size==0 and -168<=off and off+size<=16,('private write escape',off,size)
   for i in range(size):self.mem[off+i]=base.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.mem[i]for i in range(-168,16))
class Program(base.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  n={RNG:0,TRANSFORM:3,EMIT:4}[target];args=tuple(s.r[4:4+n]);packet=()
  if target==TRANSFORM:
   assert args[1]==('STACK',-16),('transform output home',args);s.exposed_output=True
  if target==EMIT:
   assert args[:2]==(('STACK',-124),255),('descriptor extent/home',args);packet=tuple(s.mem[i]for i in range(-124,-16));s.exposed_packet=True
  s.trace.append(('CALL',target,args,packet,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  for begin,end,active in((-16,-4,s.exposed_output),(-124,-16,s.exposed_packet)):
   if active:
    for off in range(begin,end):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  for i in range(4):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
def prove(raw,retail):
 terms=Terms();values=[];coverage={}
 for side,words in(('raw',raw),('retail',retail)):
  p=Program(words,terms);paths=p.paths(0,{-4:'returned'},State(side));result={}
  for key,s in paths.items():
   assert s.r[29]==('STACK',0) and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30)) and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   result[key]=(s.trace,s.read_set,s.frame(),tuple(s.r),tuple(s.f),s.hi,s.lo,s.fcsr)
  values.append(result);coverage[side]=p.seen
 a,b=values;assert a.keys()==b.keys(),('path predicates',len(a),len(b))
 for key in a:
  if a[key]!=b[key]:
   part=next(i for i,(x,y)in enumerate(zip(a[key],b[key]))if x!=y)
   if part==0:
    ta,tb=a[key][0],b[key][0];i=next((i for i,(x,y)in enumerate(zip(ta,tb))if x!=y),min(len(ta),len(tb)))
    raise AssertionError(('trace',key,i,repr(ta[i]if i<len(ta)else'<end>')[:1700],repr(tb[i]if i<len(tb)else'<end>')[:1700]))
   raise AssertionError(('transfer',key,part,repr(a[key][part])[:1700],repr(b[key][part])[:1700]))
 # Both IDO streams contain the same redundant load after an unconditional
 # return-epilogue branch. No normal control-flow edge reaches this word.
 expected=set(range(0,680,4))-{0x60}
 for side in coverage:assert coverage[side]==expected,('coverage',side,sorted(expected-coverage[side]),sorted(coverage[side]-expected))
 assert raw[0x60//4]==retail[0x60//4]==0x8C6C01D4
 return dict(paths=len(a),whole_function=True,reachable_words={k:len(v)for k,v in coverage.items()},unreachable_identical_word='0x60:8C6C01D4',ordered_FP_operands_and_FCSR=True,full184_private_and_incoming_home_bytes_at_every_call_and_return=True,complete_registers_at_return=True,all108_descriptor_bytes=True,retained_transform_output_mutation=True,c_match_credit=0)
def programs(label='raw'):return source.programs()['raw'],source.retail()

if __name__=='__main__':
 label=sys.argv[1]if len(sys.argv)>1 else'v10'
 try:report=prove(*programs(label))
 except AssertionError as error:
  (O/('proof-'+label+'.json')).write_text(json.dumps(dict(label=label,passes=False,reason=str(error),c_match_credit=0),indent=2)+'\n');raise
 (O/('proof-'+label+'.json')).write_text(json.dumps(dict(label=label,passes=True,**report),indent=2)+'\n');print(json.dumps(report),flush=True)
