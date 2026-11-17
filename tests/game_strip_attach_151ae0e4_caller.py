"""Execute the complete original selector dispatcher around the attachment."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct
from tools.tests import game_strip_attach_151ae0e4_oracle as o

CALLER=0x151AE06C
ADMIT,RESET=[o.SYMS[n]for n in('func_151ACB38','func_151AE264')]
rom=(o.source.FROZEN/'conker/conker.us.bin').read_bytes()
caller=list(struct.unpack_from('>30I',rom,CALLER-0x15000000+0x2D4B0))

class Caller(o.Oracle):
 def __init__(self,words,initial,c,admission,current,request_mutation,original=caller):
  connected={o.ENTRY+4*i:w for i,w in enumerate(words)}
  super().__init__(original,initial,c,entry=CALLER,arguments=(o.ACTOR,o.REQUEST),connected=connected)
  self.admission,self.initial_selector,self.request_mutation=admission,current,request_mutation
  self.dispatch=[];self.admission_home=None
 def record_call(self,target):
  if target in(ADMIT,RESET,o.ENTRY):
   args=tuple(self.arguments(2));self.dispatch.append((target,args))
   if target==ADMIT:
    assert args==(o.ACTOR,self.r[29]+0x1F),('admission ABI',args)
    self.admission_home=args[1]
   else:assert args==(o.ACTOR,(self.case.key+self.request_mutation)&255),('dispatch ABI',target,args)
  else:super().record_call(target)
 def hook(self,target):
  if target not in(ADMIT,RESET):return super().hook(target)
  m=self.memory
  if target==ADMIT:
   m[self.admission_home]=0xA5;m[o.REQUEST+0x1B]=(self.case.key+self.request_mutation)&255
   value=self.admission
  else:
   # Reset may change the caller's packet and selector. The dispatcher must
   # preserve the requested byte captured before this call.
   m[o.REQUEST+0x1B]^=0x5A;m[o.read(m,o.ACTOR+0x31C)+0x98]=0
   value=0xABCD1234
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value

def one(words,c,admission,current,request_mutation,original=caller):
 initial=o.fixture(c);initial[o.CHILD+0x98]=current
 machine=Caller(words,initial,c,admission,current,request_mutation,original).run()
 expected=dict(initial);expected[o.REQUEST+0x1B]=(c.key+request_mutation)&255
 key=expected[o.REQUEST+0x1B];dispatch=[(ADMIT,(o.ACTOR,machine.admission_home))];calls=[];spin=False
 if admission and(current==0 or current!=key):
  if current:
   dispatch.append((RESET,(o.ACTOR,key)));expected[o.REQUEST+0x1B]^=0x5A;expected[o.CHILD+0x98]=0
  dispatch.append((o.ENTRY,(o.ACTOR,key)))
  expected,calls,spin=o.reference(expected,replace(c,key=key))
 assert machine.dispatch==dispatch,('dispatcher',machine.dispatch,dispatch)
 assert machine.service.calls==calls and machine.spins==spin
 assert o.o.public(machine.memory)==o.o.public(expected),('public caller RAM',admission,current,request_mutation)
 if not spin:
  assert tuple(machine.r[16:24])+(machine.r[28],machine.r[29],machine.r[30])==machine.saved_g
  assert tuple(machine.f[20:])==machine.saved_fp
 return machine

def run(programs):
 seen={name:set()for name in programs};n=0
 for seed,admission,selector,mutation in itertools.product(range(8),(0,1),(0,1,0x80,0xFF),(0,1)):
  c=o.Case(seed=seed,key=(0,1,0x80,0xFF)[seed%4],count=(1,4,20,128)[seed%4],fraction=.5,gate=1 if seed==7 else 0,mutation=seed*2,phase=(seed&1)*8,threshold=seed%4)
  runs={name:one(words,c,admission,selector,mutation)for name,words in programs.items()}
  a=runs['retail']
  for name,m in runs.items():seen[name].update(m.visits);assert o.o.public(m.memory)==o.o.public(a.memory)
  assert runs['derived'].memory==a.memory and runs['derived'].fp==a.fp and runs['derived'].boundaries==a.boundaries
  n+=1
 bad=caller[:];assert bad[28]==0x03E00008
 # A corrupted packet-byte address must fail the real dispatcher contract.
 at=next(i for i,w in enumerate(bad)if w==0x91C5001B);bad[at]=0x91C5001A
 try:one(programs['retail'],o.Case(key=0x80),1,0,0,original=bad)
 except AssertionError as error:assert str(error);control=str(error)[:160]
 else:raise AssertionError('bad packet address accepted')
 return dict(cases_per_stream=n,caller_words=30,caller_coverage={name:len({at for at in visits if CALLER<=at<CALLER+120})for name,visits in seen.items()},complete_derived_RAM_private_stack_and_FP_equal=True,admission_and_packet_reload=True,reset_preserves_requested_byte=True,null_spin_propagated=True,effective_control=control)
