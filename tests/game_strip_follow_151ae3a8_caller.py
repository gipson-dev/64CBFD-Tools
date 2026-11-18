"""Complete original attachment-gated position-update caller."""
import itertools,json,struct
from tools.tests import game_strip_follow_151ae3a8_oracle as o
CALLER=0x151ACB60
rom=(o.source.FROZEN/'conker/conker.us.bin').read_bytes();caller=list(struct.unpack_from('>13I',rom,CALLER-0x15000000+0x2D4B0))
class Caller(o.Oracle):
 def __init__(self,words,m,c,original=caller):
  super().__init__(original,m,c,entry=CALLER,arguments=(o.INPUT,),connected={o.ENTRY+4*i:w for i,w in enumerate(words)})
  self.invocations=[]
 def record_call(self,target):
  if target==o.ENTRY:
   args=tuple(self.arguments(1));assert args==(o.INPUT,),('callback ABI',args);self.invocations.append(args)
  else:super().record_call(target)

def one(words,c,enabled,original=caller):
 initial=o.fixture(c)
 if not enabled:o.put(initial,o.CHILD+0x9C,0)
 m=Caller(words,initial,c,original).run()
 expected,calls=o.reference(initial,c)if enabled else(dict(initial),[])
 assert m.invocations==([(o.INPUT,)]if enabled else[])
 assert m.service.calls==calls
 assert o.o.public(m.memory)==o.o.public(expected),('caller public RAM',enabled,c)
 assert tuple(m.r[16:24])+(m.r[28],m.r[29],m.r[30])==m.saved_g
 assert tuple(m.f[20:])==m.saved_fp
 return m

def run(programs):
 seen={k:set()for k in programs};n=0
 for seed,mutation,enabled in itertools.product(range(8),range(16),(False,True)):
  c=o.Case(seed=seed,count=(0,1,4,20,128,255,20,4)[seed],spacing=(5.,140.)[seed&1],progress=(0.,.5,1.,.5)[seed%4],heading=(0,127,128,255,0x12340080,0xFFFF0081,1,0xFE)[seed],mutation=mutation,phase=(seed&1)*8,pattern=seed%5)
  runs={name:one(words,c,enabled)for name,words in programs.items()};a=runs['retail']
  for name,m in runs.items():seen[name].update(m.visits);assert o.o.public(m.memory)==o.o.public(a.memory)
  assert runs['derived'].memory==a.memory and runs['derived'].boundaries==a.boundaries and runs['derived'].fp==a.fp
  n+=1
 bad=caller[:];assert bad[8]==0xAFA40018;bad[8]=0x24840004
 try:one(programs['retail'],o.Case(),True,original=bad)
 except AssertionError as error:assert 'callback ABI'in str(error);control=str(error)
 else:raise AssertionError('wrong callback pointer accepted')
 return dict(cases_per_stream=n,caller_words=13,caller_coverage={name:len({at for at in values if CALLER<=at<CALLER+52})for name,values in seen.items()},complete_derived_RAM_private_and_FP_equal=True,attached_and_null_paths=True,one_pointer_void_ABI=True,effective_control=control)
