"""Independent symbolic entry/gate/seed transfer; no whole-function claim."""
from pathlib import Path
import json
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g

class State(e.State):
 def __init__(self):
  super().__init__('common','prefix');self.r[29]=('STACK',0);self.r[31]=('RETURN',);self.r[4]=('EFFECT',);self.effects=[];self.private_writes=[]
  self.r[16]=('ENTRY',16);self.mem={};self.fcsr=('FCSR','entry')
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0
   return self.mem.get(address[1],('PRIVATE_ENTRY',address[1]))
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0;self.mem[address[1]]=value;self.private_writes.append((address[1],size))
  else:super().store(address,size,value);self.effects.append(self.trace[-1])

class Program(e.Program):
 def __init__(self,words):super().__init__(words,b'',g.ENTRY)
 def step(self,s,w):
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op in (53,61):
   address=e.add(s.r[rs],e.signed((w&65535)|(-65536 if w&32768 else 0)))
   assert e.tagged(address,'STACK') and address[1]%8==0
   if op==61:
    s.store(address,4,s.f[rt]);s.store(e.add(address,4),4,s.f[rt+1])
   else:s.f[rt]=s.load(address,4,b'');s.f[rt+1]=s.load(e.add(address,4),4,b'')
  else:super().step(s,w)
 def call(self,s,target):
  assert target==g.SIDE and s.r[29]==('STACK',-280)
  args=tuple(s.r[4:7]);s.trace.append(('CALL',target,args,s.fcsr));s.effects.append(s.trace[-1]);ordinal=s.calls[target];s.calls[target]+=1
  for i in (1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  s.r[2]=('RESULT',target,ordinal)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  for i in range(4):s.mem[-280+4*i]=('CALL_HOME',ordinal,i)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal)

def common_prefix_trace(s):
 trace=s.trace[:];reads=[x for x in trace if x[0]=='READ'];assert len(reads)>=4
 payload=reads[0][1];assert payload==e.add(('EFFECT',),0x98)
 state=('LOAD',('LOAD',payload,4,0),4,0)
 actor=('LOAD',e.add(state,0x18),4,0)
 a=('READ',e.add(state,0x1C),1);b=('READ',e.add(actor,0x3B),1)
 # Both byte reads are ordinary mapped memory with no intervening write/call.
 # Their equality comparison is symmetric, including when the bytes alias.
 if a!=b and a in trace and b in trace:
  i,j=trace.index(a),trace.index(b);assert abs(i-j)==1,(i,j,trace)
  trace[min(i,j):max(i,j)+1]=[a,b]
 return trace

def relation(s,label):
 assert all(size==4 and off in (*range(-240,-176,4),-8) for off,size in s.private_writes),('prefix private write escape',s.private_writes)
 saved=tuple(s.mem[k] for k in (-196,-180,-184,-188,-192,-200))
 saved_fp=tuple(s.mem[k] for k in range(-240,-200,4))
 assert s.r[29]==('STACK',-280)
 live=(s.r[17],s.r[18],s.r[19],s.r[20],s.r[16],s.mem.get(-8),s.f[4]) if label in ('movement','transition') else (s.r[2],)
 return s.effects,common_prefix_trace(s),saved,saved_fp,s.mem[-180],s.r[29],s.fcsr,tuple(s.f[20:]),live

def prove(raw,retail):
 assert raw[:15]==retail[:15] and raw[0]==0x27BDFEE8
 assert raw[0x648//4:]==retail[0x648//4:]
 a=Program(raw).paths(0,{0x110:'transition',0x1A0:'movement',0x648:'return'},State())
 b=Program(retail).paths(0,{0x110:'transition',0x1A0:'movement',0x648:'return'},State())
 assert a.keys()==b.keys(),('prefix path conditions',len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
 for key in a:
  left,right=relation(a[key],key[0]),relation(b[key],key[0]);assert left==right,('prefix transfer',key,left,right)
 return dict(symbolic_paths=len(a),complete_prefix=True,all_entry_gates=True,initialization_copy_and_flags=True,
             opaque_query_providers=True,branch_likely_annul=True,identity_byte_read_commute=True,
             frame_and_saved_pairs_identical=True,whole_function=False,ordered_FP_body_proved=False)
