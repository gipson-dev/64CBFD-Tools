"""Symbolic post-query cleanup/transition transfer with byte-precise stack."""
from pathlib import Path
import json
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g

def byte(value,shift):
 if isinstance(value,int):return(value>>shift)&255
 if shift==0 and e.tagged(value,'AND') and value[2]==255:return value
 return('BYTE',value,shift)
def word(values):
 if all(isinstance(v,int) for v in values):return sum(v<<(24-8*i) for i,v in enumerate(values))
 if all(e.tagged(v,'BYTE') for v in values) and [v[2] for v in values]==[24,16,8,0] and all(v[1]==values[0][1] for v in values):return values[0][1]
 return('WORD',tuple(values))
class State(e.State):
 def __init__(self):
  super().__init__('common','transition');self.mem={};self.r[29]=('STACK',-280);self.r[17]=('EFFECT',);self.r[19]=('PAYLOAD',);self.r[20]=('ACTOR',);self.effects=[];self.private_writes=[]
  self.r[16]=e.add(('EFFECT',),16)
  self.fcsr=('ENTRY_FCSR',);self.r[31]=('AFTER_QUERY',)
 def load(self,address,size,pool):
  if not e.tagged(address,'STACK'):return super().load(address,size,pool)
  assert size in (1,4) and (size==1 or address[1]%4==0)
  values=[self.mem.get(address[1]+i,('PRIVATE_BYTE',address[1]+i)) for i in range(size)]
  return values[0] if size==1 else word(values)
 def store(self,address,size,value):
  if not e.tagged(address,'STACK'):
   super().store(address,size,value);self.effects.append(self.trace[-1]);return
  assert size in (1,4) and (size==1 or address[1]%4==0)
  self.private_writes.append((address[1],size))
  for i in range(size):self.mem[address[1]+i]=byte(value,8*(size-1-i))

class Program(e.Program):
 def __init__(self,words):super().__init__(words,b'',g.ENTRY)
 def call(self,s,target):
  assert target in (g.CLEAN,g.FACTORY,g.COPY) and s.r[29]==('STACK',-280)
  n={g.CLEAN:1,g.FACTORY:8,g.COPY:3}[target];args=s.r[4:4+min(n,4)]
  if n>4:args += [s.load(e.add(s.r[29],16+4*i),4,b'') for i in range(n-4)]
  ordinal=s.calls[target];s.calls[target]+=1
  if target==g.COPY:
   assert args[1]==('STACK',-44) and args[2]==8,('transition copy extent/home changed',args)
   packet=tuple(s.load(e.add(args[1],i),1,b'') for i in range(8))
   s.trace.append(('COPY',target,args[0],args[1],8,packet,s.fcsr))
  else:
   for a in args:e.plain(a)
   s.trace.append(('CALL',target,tuple(args),s.fcsr))
  s.effects.append(s.trace[-1])
  for i in (1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',target,ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',target,ordinal,i)
  for i in range(4):s.store(('STACK',-280+4*i),4,('CALL_HOME',target,ordinal,i))
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',target,ordinal)
  s.hi=('CALL_HI',target,ordinal);s.lo=('CALL_LO',target,ordinal);s.fcsr=('CALL_FCSR',target,ordinal)

def relation(s):
 assert all((size==4 and off in (-280,-276,-272,-268,-264,-260,-256,-252,-44)) or(size==1 and off==-40) for off,size in s.private_writes),('transition private write escape',s.private_writes)
 assert s.r[2]==1 and s.r[29]==('STACK',-280)
 assert all(s.r[i]==('ENTRY',i) for i in (21,22,23,28,30))
 assert tuple(s.f[20:])==tuple(('ENTRY_FP',i) for i in range(20,32))
 return s.effects,s.trace,s.r[2],s.r[17],s.r[19],s.r[20],s.r[29],tuple(s.f[20:]),s.fcsr
def prove(raw,retail):
 a=Program(raw).paths(0x110,{0x648:'return'},State());b=Program(retail).paths(0x110,{0x648:'return'},State())
 assert a.keys()==b.keys(),('transition path conditions',len(a),len(b))
 for key in a:
  x,y=relation(a[key]),relation(b[key]);assert x==y,('transition transfer',key,x,y)
  copies=[event for event in x[0] if event[0]=='COPY']
  if copies:
   assert len(copies)==1 and copies[0][-2][-3:]==tuple(('PRIVATE_BYTE',off) for off in (-39,-38,-37))
 return dict(symbolic_paths=len(a),owner_reloaded_after_cleanup=True,all_eight_transition_bytes=True,
             untouched_byte_offsets=[-39,-38,-37],factory_arguments=8,live_mode_after_factory_copy=True,
             opaque_public_mutations_and_FCSR=True,whole_function=False,raw_fault_state_claimed=False)
