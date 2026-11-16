"""Instruction-driven two-path FP/FCSR, complete packet/frame and ABI relation."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct,sys,time,traceback
from tools.experiments import game_composite_burst_151a2f0c_recovery as m
from tools.tests import game_growth_curve_151a1fb4_proof as base
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
e=base.e;ENTRY=0x151A2F0C;SUBMIT=0x15152B38

class State(base.State):
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0
   assert -144<=off and off+size<=0,('private read escape',off,size)
   return base.join([self.mem.get(off+i,('PRIVATE_BYTE',off+i))for i in range(size)])
  e.plain(address);self.read_set[self.epoch,address,size]+=1
  return('LOAD',address,size,self.epoch)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0
   assert -144<=off and off+size<=0,('private write escape',off,size)
   for i in range(size):self.mem[off+i]=base.byte(value,8*(size-i-1))
  else:
   e.plain(address);e.plain(value);self.trace.append(('WRITE',address,size,e.bitop('AND',value,(1<<(8*size))-1)));self.epoch+=1
 def frame(self):return tuple(self.load(('STACK',off),1)for off in range(-144,0))

class Program(base.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target==SUBMIT;args=tuple(s.r[4:7]);assert args[0]==('STACK',-116),('packet home',args)
  packet=tuple(s.load(('STACK',off),1)for off in range(-116,0))
  s.trace.append(('CALL',target,args,packet,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  for off in range(-116,0):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  for i in range(4):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal)
  s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)

def prove(raw,retail):
 terms=Terms();programs={side:Program(words,terms)for side,words in(('raw',raw),('retail',retail))};values={}
 for side,p in programs.items():
  paths=p.paths(0,{-4:'return'},State(side));result={}
  for key,s in paths.items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
   assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   result[key]=(s.trace,s.read_set,s.fcsr,s.frame(),tuple(s.r),tuple(s.f),s.hi,s.lo)
  values[side]=result
 assert values['raw'].keys()==values['retail'].keys(),('path predicates',values['raw'].keys(),values['retail'].keys())
 for key,a in values['raw'].items():
  b=values['retail'][key]
  if a!=b:
   part=next(i for i,(x,y)in enumerate(zip(a,b))if x!=y)
   if part==0:
    at=next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),None)
    raise AssertionError(('transfer trace',key,at,repr(a[0][at]if at is not None else a[0])[:2000],repr(b[0][at]if at is not None else b[0])[:2000]))
   raise AssertionError(('transfer part',key,part,repr(a[part])[:2000],repr(b[part])[:2000]))
 assert len(values['raw'])==2
 for side,p in programs.items():assert p.seen==set(range(0,len(p.words)*4,4)),('unproved instructions',side)
 return dict(paths=2,whole_function=True,all_words_covered={side:len(p.seen)for side,p in programs.items()},ordered_FP_and_FCSR=True,full_private_frame_at_call_and_return=True,complete_registers_at_return=True,arbitrary_public_aliases=True,provider_packet_mutation=True,c_match_credit=0)

def main():
 from tools.experiments.game_composite_burst_151a2f0c_match import fields
 m.check_inputs();raw,refs=payload(m.OUT/'qualified.o',m.NAME);words=bound_blob(raw,refs,m.symbols());truth=m.retail()
 report=prove(words,truth);controls=[]
 def run(label,candidate,good):
  try:prove(candidate,truth)
  except AssertionError as error:
   reason=str(error);assert not good and reason and not any(x in reason for x in('unsupported','unbounded','escape','BREAK')),('invalid control',label,reason)
   controls.append(dict(label=label,rejected=True,reason=reason[:800]))
  else:assert good,('ineffective control',label);controls.append(dict(label=label,passes=True))
 alternate=[]
 for w in words:
  for shift,kind in fields(w):
   if kind=='g'and w>>shift&31 in(8,9):w=(w&~(31<<shift))|((17-(w>>shift&31))<<shift)
  alternate.append(w)
 run('independent-T0-T1-allocation',alternate,True)
 for label,find,change in(
  ('wrong-flag-bit',lambda w:w>>26==12 and w&65535==0x1000,lambda w:w^1),
  ('mode-byte-offset',lambda w:w>>26==36 and w>>16&31==5,lambda w:w+1),
  ('FP-operand-order',lambda w:w>>26==17 and w>>21&31==16 and w&63==0 and w>>11&31!=w>>16&31,lambda w:(w&~((31<<11)|(31<<16)))|((w>>11&31)<<16)|((w>>16&31)<<11)),
  ('tail-byte-offset',lambda w:w>>26==40 and w&65535==0x8F,lambda w:w-1)):
  at=next(i for i,w in enumerate(words)if find(w));bad=words[:];bad[at]=change(bad[at]);run(label,bad,False)
 bad=words[:];assert bad[-1]==0;bad[-1]=0xAFA0FF80;run('private-gap-write-in-return-delay',bad,False)
 report.update(controls=controls,source_installed=m.installed(),raw_sha256=hashlib.sha256(raw).hexdigest())
 (m.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
