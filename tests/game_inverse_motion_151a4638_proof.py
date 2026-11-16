"""Whole eight-path constructor relation, independent of any normalization."""
from pathlib import Path
import hashlib,json,struct,sys
from tools.tests import game_growth_curve_151a1fb4_proof as base
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_inverse_motion_151a4638_recovery as source
O=source.OUT;R=source.ROOT;ENTRY=source.ENTRY
RNG,REAL,FACTORY,COPY=0x150ADA20,0x150ADA68,0x15130374,0x10022EC0;e=base.e

class State(base.State):
 def __init__(self,side):
  super().__init__(side);self.r[6]=('Z',);self.r[7]=('VX',);self.f[12]=('X',);self.f[14]=('Y',)
  self.mem={off:('PRIVATE_BYTE',off)for off in range(-168,28)}
  for off,value in((16,('VY',)),(20,('VZ',)),(24,('OWNER',))):self.store(('STACK',off),4,value)
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert off%size==0 and -168<=off and off+size<=28,('private read escape',off,size)
   return base.join([self.mem[off+i]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert off%size==0 and -168<=off and off+size<=28,('private write escape',off,size)
   for i in range(size):self.mem[off+i]=base.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.mem[i]for i in range(-168,28))

class Program(base.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def step(self,s,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:
   fs,fd=w>>11&31,w>>6&31;event=(16,7,(s.f[fs],),s.fcsr);s.trace.append(('FP',event));s.f[fd]=self.terms.term('FP_VALUE',*event);s.fcsr=self.terms.term('FP_STATUS',*event)
  else:super().step(s,w)
 def call(self,s,target):
  counts={RNG:0,REAL:0,FACTORY:5,COPY:3};assert target in counts,hex(target);n=counts[target]
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,n-4)))
  packet=()
  if target==FACTORY:
   assert args[0:3]==(('STACK',-112),0,12)and args[4]==1,('factory ABI',args)
   packet=tuple(s.mem[off]for off in range(-112,0))
  elif target==COPY:
   assert args[1:]==(('STACK',-128),12),('parameter home/extent',args)
   packet=tuple(s.mem[off]for off in range(-128,-116))
  s.trace.append(('CALL',target,args,packet,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  if target==FACTORY:
   for off in range(-112,0):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  if target==COPY:
   for i,value in enumerate(packet):s.store(e.add(args[0],i),1,value)
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  for i in range(max(4,n)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=args[0]if target==COPY else('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('RESULT_FP',target,ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)

def prove(raw,retail):
 terms=Terms();values=[];coverage={}
 for side,words in(('raw',raw),('retail',retail)):
  p=Program(words,terms);paths=p.paths(0,{-4:'returned'},State(side));result={}
  for key,s in paths.items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   result[key]=(s.trace,s.read_set,s.frame(),tuple(s.r),tuple(s.f),s.hi,s.lo,s.fcsr,s.divisors)
  values.append(result);coverage[side]=p.seen
 a,b=values;assert a.keys()==b.keys(),('path predicates',a.keys(),b.keys())
 for key in a:
  if a[key]!=b[key]:
   part=next(i for i,(x,y)in enumerate(zip(a[key],b[key]))if x!=y)
   if part==0:
    i=next((i for i,(x,y)in enumerate(zip(a[key][0],b[key][0]))if x!=y),None)
    raise AssertionError(('trace',key,i,repr(a[key][0][i])[:1600],repr(b[key][0][i])[:1600]))
   raise AssertionError(('transfer',key,part,repr(a[key][part])[:1600],repr(b[key][part])[:1600]))
 assert len(a)==8,len(a)
 for side,words in(('raw',raw),('retail',retail)):assert coverage[side]==set(range(0,len(words)*4,4)),('unproved instructions',side,sorted(set(range(0,len(words)*4,4))-coverage[side]))
 return dict(paths=8,whole_function=True,all_words_covered={k:len(v)for k,v in coverage.items()},ordered_FP_operands_and_FCSR=True,full_private_frame_and_incoming_homes_at_every_call_and_return=True,complete_registers_at_return=True,explicit_seven_argument_ABI=True,all112_factory_bytes_and12_parameter_bytes=True,provider_packet_mutation=True,c_match_credit=0)

def programs(label='raw'):return source.programs()['raw'],source.retail()

if __name__=='__main__':
 label=sys.argv[1]if len(sys.argv)>1 else'v3'
 try:report=prove(*programs(label))
 except AssertionError as error:
  report=dict(label=label,passes=False,reason=str(error),c_match_credit=0);(O/('proof-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');raise
 (O/('proof-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(label=label,**report)),flush=True)
